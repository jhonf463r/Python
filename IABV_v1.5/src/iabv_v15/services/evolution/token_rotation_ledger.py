"""TokenRotationLedger — registro operativo de eventos de auth.

Capa 2.2 de IABV v1.5. El objetivo es que el sistema deje de enterarse
"de casualidad" que un PAT de GitHub o la Devin API key expiraron: cada
probe (200 OK / 401 / rotacion confirmada) queda persistido y
``OperationalSelfExaminationService`` puede proyectar cuando conviene
disparar ``scripts/rotate_tokens.ps1`` antes de que el usuario lo note.

Contratos respetados (ver AGENTS.md):

- No es otro cerebro. No decide rutas ni corre ps1. Solo observa y
  proyecta.
- No duplica ``PerceptionSnapshot``: es un ledger append-only, no una
  percepcion.
- No toca capas P1-P4. OSES lo consume como dep opcional.
- Read-only sobre el sistema vivo: el unico side effect es persistir su
  propio JSON en ``data/evolution/token_rotations/``.

Eventos registrados (``TokenLedgerEvent.kind``):

- ``probe_ok``: endpoint respondio 2xx con el token actual.
- ``probe_failed``: endpoint respondio 401/403 o fallo de auth. Es la
  senal mas fuerte de que el token caduco.
- ``rotated``: ``rotate_tokens.ps1`` (o un humano) reemplazo el token y
  el nuevo quedo validado. Cada ``rotated`` arranca una "vida" nueva.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)


_KIND_PROBE_OK = 'probe_ok'
_KIND_PROBE_FAILED = 'probe_failed'
_KIND_ROTATED = 'rotated'
_ALLOWED_KINDS = frozenset({_KIND_PROBE_OK, _KIND_PROBE_FAILED, _KIND_ROTATED})

# Techo duro de eventos por token. Evita que el ledger crezca infinito
# en sesiones que corren ``run_self_audit`` cada minuto. Mantiene los
# mas recientes, que son los unicos que importan para la prediccion.
_MAX_EVENTS_PER_TOKEN = 500


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return _utc_now()
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return _utc_now()


class TokenRotationLedger:
    """Registro persistente y thread-safe de eventos de auth por token.

    Uso tipico:

        ledger = TokenRotationLedger(workspace_root)
        ledger.record_probe('github_api', ok=True)          # desde SelfAudit
        ledger.record_probe('devin_api', ok=False, reason='401')
        ledger.record_rotation('github_api')                # desde bootstrap
        prediction = ledger.prediction('github_api')

    El servicio ``OperationalSelfExaminationService`` luego lee
    ``prediction`` + ``recent_failures`` para emitir findings HIGH/MEDIUM
    con ``recommendation='Ejecutar scripts/rotate_tokens.ps1'`` cuando
    corresponda.
    """

    FILENAME = 'latest.json'
    SUBDIR = Path('evolution') / 'token_rotations'

    # Si un token no se valida OK hace mas de este intervalo, lo marcamos
    # stale. No implica caducidad real, pero si perdida de observabilidad.
    STALE_THRESHOLD = timedelta(hours=36)

    # Ventana para considerar el intervalo entre rotaciones. Un token
    # rotado hace 60 dias no dice nada sobre el patron actual.
    ROTATION_HISTORY_WINDOW = timedelta(days=180)

    # Cuando el proximo expiry proyectado queda a menos de esto del
    # ``now()``, OSES debe subir el finding a HIGH y recomendar rotar ya.
    PROACTIVE_ROTATION_LEAD = timedelta(days=2)

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        clock: Any | None = None,
    ) -> None:
        self._root = Path(workspace_root) / 'data' / self.SUBDIR
        self._ledger_path = self._root / self.FILENAME
        self._lock = threading.Lock()
        self._clock = clock or _utc_now

    # ------------------------------------------------------------------
    # API de escritura
    # ------------------------------------------------------------------

    def record_probe(
        self,
        token_name: str,
        *,
        ok: bool,
        reason: str | None = None,
        observed_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Registra un probe de auth. ``ok=True`` -> ``probe_ok``.

        Detecta rotacion implicita: si el evento anterior del mismo token
        era ``probe_failed`` y este nuevo probe es ``ok``, inserta
        automaticamente un ``rotated`` justo antes. Asi ``rotate_tokens.ps1``
        no tiene que llamar una API nueva para que OSES aprenda el patron:
        la re-emergencia del OK ES la rotacion.
        """

        kind = _KIND_PROBE_OK if ok else _KIND_PROBE_FAILED
        ts = _coerce_dt(observed_at or self._clock())
        # La lectura del ultimo evento y el append van bajo el mismo lock:
        # dos probe_ok concurrentes posteriores a un probe_failed no deben
        # insertar dos ``rotated`` duplicados (TOCTOU).
        with self._lock:
            events_to_append: list[dict[str, Any]] = []
            if ok:
                last_kind = self._last_event_kind_unlocked(token_name)
                if last_kind == _KIND_PROBE_FAILED:
                    events_to_append.append(
                        {
                            'kind': _KIND_ROTATED,
                            'observed_at': ts.isoformat(),
                            'reason': 'implicit_rotation_after_failure',
                            'metadata': {'trigger': 'probe_ok_after_probe_failed'},
                        }
                    )
            probe_event = {
                'kind': kind,
                'observed_at': ts.isoformat(),
                'reason': reason or None,
                'metadata': dict(metadata or {}),
            }
            events_to_append.append(probe_event)
            self._append_events_unlocked(token_name, events_to_append)
        return probe_event

    def record_rotation(
        self,
        token_name: str,
        *,
        rotated_at: datetime | None = None,
        reason: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Registra que el token fue reemplazado por uno nuevo valido."""

        return self._append_event(
            token_name=token_name,
            kind=_KIND_ROTATED,
            observed_at=rotated_at,
            reason=reason,
            metadata=metadata,
        )

    # ------------------------------------------------------------------
    # API de lectura / prediccion
    # ------------------------------------------------------------------

    def events(self, token_name: str | None = None) -> list[dict[str, Any]]:
        data = self._load()
        all_events: list[dict[str, Any]] = []
        for name, bucket in data.get('tokens', {}).items():
            if token_name and name != token_name:
                continue
            for event in bucket.get('events', []):
                all_events.append({**event, 'token_name': name})
        all_events.sort(key=lambda ev: ev.get('observed_at', ''))
        return all_events

    def tracked_tokens(self) -> list[str]:
        return sorted(self._load().get('tokens', {}).keys())

    def prediction(self, token_name: str) -> dict[str, Any] | None:
        """Proyeccion sobre el token. ``None`` si no hay eventos."""

        events = self.events(token_name=token_name)
        if not events:
            return None
        now = self._clock()

        rotations = [
            _coerce_dt(ev['observed_at'])
            for ev in events
            if ev.get('kind') == _KIND_ROTATED
        ]
        # Solo tomamos rotaciones recientes para el promedio: un patron
        # antiguo no refleja el ritmo actual.
        recent_rotations = [
            ts for ts in rotations
            if now - ts <= self.ROTATION_HISTORY_WINDOW
        ]
        intervals_days: list[float] = []
        for earlier, later in zip(recent_rotations, recent_rotations[1:]):
            interval = (later - earlier).total_seconds() / 86400.0
            if interval > 0:
                intervals_days.append(interval)
        avg_interval_days = (
            sum(intervals_days) / len(intervals_days) if intervals_days else None
        )

        last_ok = next(
            (
                _coerce_dt(ev['observed_at'])
                for ev in reversed(events)
                if ev.get('kind') == _KIND_PROBE_OK
            ),
            None,
        )
        last_failure = next(
            (
                _coerce_dt(ev['observed_at'])
                for ev in reversed(events)
                if ev.get('kind') == _KIND_PROBE_FAILED
            ),
            None,
        )
        last_rotation = recent_rotations[-1] if recent_rotations else None

        projected_expiry_at: datetime | None = None
        days_until_projected: float | None = None
        if last_rotation is not None and avg_interval_days is not None:
            projected_expiry_at = last_rotation + timedelta(days=avg_interval_days)
            days_until_projected = (projected_expiry_at - now).total_seconds() / 86400.0

        stale = bool(
            last_ok is not None
            and (now - last_ok) > self.STALE_THRESHOLD
        )

        # Token expirado en vivo: la ultima observacion fue un 401/403.
        expired_live = bool(
            last_failure is not None
            and (last_ok is None or last_failure > last_ok)
        )

        proactive_due = bool(
            projected_expiry_at is not None
            and days_until_projected is not None
            and days_until_projected <= self.PROACTIVE_ROTATION_LEAD.total_seconds() / 86400.0
        )

        return {
            'token_name': token_name,
            'last_probe_ok_at': last_ok.isoformat() if last_ok else None,
            'last_probe_failed_at': last_failure.isoformat() if last_failure else None,
            'last_rotation_at': last_rotation.isoformat() if last_rotation else None,
            'rotations_observed': len(recent_rotations),
            'avg_interval_days': avg_interval_days,
            'projected_expiry_at': (
                projected_expiry_at.isoformat() if projected_expiry_at else None
            ),
            'days_until_projected_expiry': days_until_projected,
            'stale': stale,
            'expired_live': expired_live,
            'proactive_due': proactive_due,
            'evaluated_at': now.isoformat(),
        }

    def predictions(self, token_names: Iterable[str] | None = None) -> list[dict[str, Any]]:
        names = list(token_names) if token_names is not None else self.tracked_tokens()
        out: list[dict[str, Any]] = []
        for name in names:
            pred = self.prediction(name)
            if pred is not None:
                out.append(pred)
        return out

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _last_event_kind(self, token_name: str) -> str | None:
        """Wrapper publico que toma el lock. Usar ``_last_event_kind_unlocked``
        cuando ya se tiene el lock (e.g. ``record_probe``)."""
        with self._lock:
            return self._last_event_kind_unlocked(token_name)

    def _last_event_kind_unlocked(self, token_name: str) -> str | None:
        data = self._load()
        bucket = data.get('tokens', {}).get(token_name)
        if not bucket:
            return None
        events = bucket.get('events') or []
        if not events:
            return None
        return str(events[-1].get('kind') or '') or None

    def _append_events_unlocked(
        self,
        token_name: str,
        new_events: list[dict[str, Any]],
    ) -> None:
        """Append N eventos al bucket de ``token_name`` bajo el lock ya
        adquirido por el caller. Un solo load + write por batch."""
        if not new_events:
            return
        data = self._load()
        bucket = data.setdefault('tokens', {}).setdefault(
            token_name, {'events': []}
        )
        events = bucket['events']
        events.extend(new_events)
        if len(events) > _MAX_EVENTS_PER_TOKEN:
            del events[: len(events) - _MAX_EVENTS_PER_TOKEN]
        data['updated_at'] = self._clock().isoformat()
        self._write(data)

    def _append_event(
        self,
        *,
        token_name: str,
        kind: str,
        observed_at: datetime | None,
        reason: str | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if kind not in _ALLOWED_KINDS:
            raise ValueError(f"kind desconocido: {kind!r}")
        ts = _coerce_dt(observed_at or self._clock())
        event = {
            'kind': kind,
            'observed_at': ts.isoformat(),
            'reason': reason or None,
            'metadata': dict(metadata or {}),
        }
        with self._lock:
            self._append_events_unlocked(token_name, [event])
        return event

    def _load(self) -> dict[str, Any]:
        if not self._ledger_path.exists():
            return {'tokens': {}}
        try:
            raw = self._ledger_path.read_text(encoding='utf-8')
            payload = json.loads(raw) if raw.strip() else {}
            if not isinstance(payload, dict):
                return {'tokens': {}}
            tokens = payload.get('tokens')
            if not isinstance(tokens, dict):
                payload['tokens'] = {}
            return payload
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning('TokenRotationLedger: no pude leer %s (%s)', self._ledger_path, exc)
            return {'tokens': {}}

    def _write(self, data: dict[str, Any]) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        tmp = self._ledger_path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding='utf-8')
        tmp.replace(self._ledger_path)
