"""AccountLedgerService — gestion autonoma de cuentas por proveedor.

Capa complementaria a ``TokenRotationLedger`` (que maneja auth/tokens).
Este servicio maneja cuota, limites, rotacion de cuentas y proyeccion
de agotamiento. El sistema puede rotar cuentas SIN pedir permiso cuando
la activa se agota, y notifica al usuario UNA vez si no hay mas cuentas.

Contratos respetados (ver AGENTS.md):

- No es otro cerebro. No decide rutas ni ejecuta tareas. Solo observa
  cuota, rota cuentas y proyecta agotamiento.
- No duplica ``PerceptionSnapshot``: es un ledger de cuentas, no una
  percepcion.
- No toca capas P1-P4. OSES y WorldModel lo consumen como dep opcional.
- Las credenciales NO se almacenan aqui: solo ``credential_ref`` que
  apunta a ``~/.iabv_secrets.ps1``.
- Persistencia en ``data/evolution/account_ledger/``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)


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


# -----------------------------------------------------------------------
# AccountEntry — modelo de datos de una cuenta
# -----------------------------------------------------------------------

class AccountEntry:
    """Representacion de una cuenta registrada en el ledger."""

    __slots__ = (
        'account_id', 'provider', 'email', 'credential_ref', 'status',
        'messages_used', 'messages_limit', 'reset_at', 'last_used',
        'success_rate', 'total_requests', 'successful_requests',
        'metadata', 'created_at',
    )

    def __init__(
        self,
        provider: str,
        email: str,
        credential_ref: str,
        *,
        account_id: str | None = None,
        status: str = 'active',
        messages_used: int = 0,
        messages_limit: int = 0,
        reset_at: datetime | str | None = None,
        last_used: datetime | str | None = None,
        success_rate: float = 1.0,
        total_requests: int = 0,
        successful_requests: int = 0,
        metadata: dict[str, Any] | None = None,
        created_at: datetime | str | None = None,
    ) -> None:
        self.account_id = account_id or str(uuid4())
        self.provider = provider
        self.email = email
        self.credential_ref = credential_ref
        self.status = status
        self.messages_used = messages_used
        self.messages_limit = messages_limit
        self.reset_at = _coerce_dt(reset_at) if reset_at else None
        self.last_used = _coerce_dt(last_used) if last_used else None
        self.success_rate = success_rate
        self.total_requests = total_requests
        self.successful_requests = successful_requests
        self.metadata = dict(metadata or {})
        self.created_at = _coerce_dt(created_at) if created_at else _utc_now()

    # -- serializacion --

    def to_dict(self) -> dict[str, Any]:
        return {
            'account_id': self.account_id,
            'provider': self.provider,
            'email': self.email,
            'credential_ref': self.credential_ref,
            'status': self.status,
            'messages_used': self.messages_used,
            'messages_limit': self.messages_limit,
            'reset_at': self.reset_at.isoformat() if self.reset_at else None,
            'last_used': self.last_used.isoformat() if self.last_used else None,
            'success_rate': round(self.success_rate, 4),
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AccountEntry:
        return cls(
            provider=data.get('provider', ''),
            email=data.get('email', ''),
            credential_ref=data.get('credential_ref', ''),
            account_id=data.get('account_id'),
            status=data.get('status', 'active'),
            messages_used=int(data.get('messages_used', 0)),
            messages_limit=int(data.get('messages_limit', 0)),
            reset_at=data.get('reset_at'),
            last_used=data.get('last_used'),
            success_rate=float(data.get('success_rate', 1.0)),
            total_requests=int(data.get('total_requests', 0)),
            successful_requests=int(data.get('successful_requests', 0)),
            metadata=data.get('metadata'),
            created_at=data.get('created_at'),
        )

    @property
    def messages_remaining(self) -> int:
        if self.messages_limit <= 0:
            return 999999
        return max(0, self.messages_limit - self.messages_used)

    @property
    def is_exhausted(self) -> bool:
        if self.messages_limit <= 0:
            return False
        return self.messages_used >= self.messages_limit

    @property
    def quota_fraction(self) -> float:
        if self.messages_limit <= 0:
            return 1.0
        return max(0.0, 1.0 - (self.messages_used / self.messages_limit))


# -----------------------------------------------------------------------
# AccountLedgerService
# -----------------------------------------------------------------------

class AccountLedgerService:
    """Gestion autonoma de cuentas: registro, rotacion, uso, proyeccion.

    Uso tipico:

        ledger = AccountLedgerService(workspace_root)
        ledger.register_account('chatgpt', 'user@mail.com', '$env:CHATGPT_KEY_1')
        active = ledger.get_active_account('chatgpt')
        ledger.record_usage('chatgpt', messages_used=45, messages_limit=50, reset_at=...)
        if active.is_exhausted:
            new_active = ledger.rotate_account('chatgpt')
    """

    SUBDIR = Path('evolution') / 'account_ledger'
    ACCOUNTS_FILE = 'accounts.json'
    USAGE_LOG_FILE = 'usage_log.jsonl'

    KNOWN_PROVIDERS = frozenset({
        'devin', 'chatgpt', 'claude', 'codex', 'ollama',
        'github_copilot', 'gemini', 'mistral',
    })

    # Proveedores locales: no tienen cuota de mensajes
    LOCAL_PROVIDERS = frozenset({'ollama'})

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        clock: Any | None = None,
    ) -> None:
        self._root = Path(workspace_root) / 'data' / self.SUBDIR
        self._accounts_path = self._root / self.ACCOUNTS_FILE
        self._usage_log_path = self._root / self.USAGE_LOG_FILE
        self._lock = threading.Lock()
        self._clock = clock or _utc_now
        self._user_notified_no_accounts: set[str] = set()

    # ------------------------------------------------------------------
    # Registro de cuentas
    # ------------------------------------------------------------------

    def register_account(
        self,
        provider: str,
        email: str,
        credential_ref: str,
        *,
        messages_limit: int = 0,
        reset_at: datetime | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AccountEntry:
        """Registra una cuenta nueva. Si ya existe (provider+email), actualiza."""
        provider = provider.strip().lower()
        entry = AccountEntry(
            provider=provider,
            email=email,
            credential_ref=credential_ref,
            messages_limit=messages_limit,
            reset_at=reset_at,
            metadata=metadata,
        )
        with self._lock:
            data = self._load_unlocked()
            accounts = data.setdefault('accounts', [])
            # Upsert: si ya existe la combinacion provider+email, actualiza
            for i, existing in enumerate(accounts):
                if existing.get('provider') == provider and existing.get('email') == email:
                    entry.account_id = existing.get('account_id', entry.account_id)
                    entry.created_at = _coerce_dt(existing.get('created_at')) if existing.get('created_at') else entry.created_at
                    entry.total_requests = int(existing.get('total_requests', 0))
                    entry.successful_requests = int(existing.get('successful_requests', 0))
                    entry.success_rate = float(existing.get('success_rate', 1.0))
                    accounts[i] = entry.to_dict()
                    self._save_unlocked(data)
                    self._log_usage_event('account_updated', provider, email, entry.to_dict())
                    logger.info('account_ledger: updated %s/%s', provider, email)
                    return entry
            accounts.append(entry.to_dict())
            # Si es la primera cuenta de este provider, marcarla como activa
            if not data.get('active_accounts'):
                data['active_accounts'] = {}
            if provider not in data['active_accounts']:
                data['active_accounts'][provider] = entry.account_id
            self._save_unlocked(data)
        self._log_usage_event('account_registered', provider, email, entry.to_dict())
        logger.info('account_ledger: registered %s/%s', provider, email)
        return entry

    def unregister_account(self, provider: str, email: str) -> bool:
        """Elimina una cuenta del ledger. Retorna True si existia."""
        provider = provider.strip().lower()
        with self._lock:
            data = self._load_unlocked()
            accounts = data.get('accounts', [])
            original_len = len(accounts)
            accounts = [
                a for a in accounts
                if not (a.get('provider') == provider and a.get('email') == email)
            ]
            if len(accounts) == original_len:
                return False
            data['accounts'] = accounts
            # Si era la activa, limpiar
            active = data.get('active_accounts', {})
            removed_ids = {
                a.get('account_id') for a in data.get('accounts', [])
                if a.get('provider') == provider and a.get('email') == email
            }
            if active.get(provider) in removed_ids or not any(
                a.get('provider') == provider for a in accounts
            ):
                active.pop(provider, None)
            self._save_unlocked(data)
        self._log_usage_event('account_unregistered', provider, email, {})
        return True

    # ------------------------------------------------------------------
    # Consulta de cuentas
    # ------------------------------------------------------------------

    def get_active_account(self, provider: str) -> AccountEntry | None:
        """Retorna la cuenta activa para un provider, o None."""
        provider = provider.strip().lower()
        data = self._load()
        active_id = data.get('active_accounts', {}).get(provider)
        if not active_id:
            # Fallback: primera cuenta activa del provider
            for acct in data.get('accounts', []):
                if acct.get('provider') == provider and acct.get('status') != 'disabled':
                    return AccountEntry.from_dict(acct)
            return None
        for acct in data.get('accounts', []):
            if acct.get('account_id') == active_id:
                return AccountEntry.from_dict(acct)
        return None

    def get_available_accounts(self, provider: str) -> list[AccountEntry]:
        """Retorna todas las cuentas no-disabled de un provider."""
        provider = provider.strip().lower()
        data = self._load()
        results: list[AccountEntry] = []
        for acct in data.get('accounts', []):
            if acct.get('provider') == provider and acct.get('status') != 'disabled':
                results.append(AccountEntry.from_dict(acct))
        return results

    def get_all_accounts(self) -> list[AccountEntry]:
        """Retorna todas las cuentas registradas."""
        data = self._load()
        return [AccountEntry.from_dict(a) for a in data.get('accounts', [])]

    # ------------------------------------------------------------------
    # Rotacion autonoma
    # ------------------------------------------------------------------

    def rotate_account(self, provider: str) -> AccountEntry | None:
        """Rota a la siguiente cuenta disponible del provider.

        Orden de preferencia:
        1. Cuentas con cuota restante (mayor cuota primero)
        2. Cuentas con mejor success_rate
        3. Cuentas cuyo reset_at ya paso (cuota renovada)

        Si no hay mas cuentas disponibles, retorna None y marca el
        provider como sin cuentas (para notificar al usuario UNA vez).
        """
        provider = provider.strip().lower()
        now = self._clock()

        with self._lock:
            data = self._load_unlocked()
            current_active_id = data.get('active_accounts', {}).get(provider)
            candidates: list[AccountEntry] = []

            for acct_dict in data.get('accounts', []):
                if acct_dict.get('provider') != provider:
                    continue
                if acct_dict.get('status') == 'disabled':
                    continue
                acct = AccountEntry.from_dict(acct_dict)
                # Si el reset_at ya paso, renovar cuota
                if acct.reset_at and acct.reset_at <= now:
                    acct.messages_used = 0
                    acct.status = 'active'
                if acct.account_id == current_active_id:
                    # Marcar la actual como agotada
                    acct.status = 'exhausted'
                    self._update_account_unlocked(data, acct)
                    continue
                if not acct.is_exhausted:
                    candidates.append(acct)

            if not candidates:
                self._save_unlocked(data)
                self._log_usage_event('rotation_failed', provider, '', {
                    'reason': 'no_available_accounts',
                })
                if provider not in self._user_notified_no_accounts:
                    self._user_notified_no_accounts.add(provider)
                    logger.warning(
                        'account_ledger: NO hay mas cuentas disponibles para %s. '
                        'Notificar al usuario y considerar fallback a ollama.',
                        provider,
                    )
                return None

            # Ordenar: mayor cuota restante * success_rate
            candidates.sort(
                key=lambda a: (a.quota_fraction * a.success_rate, a.messages_remaining),
                reverse=True,
            )
            best = candidates[0]
            data.setdefault('active_accounts', {})[provider] = best.account_id
            best.status = 'active'
            self._update_account_unlocked(data, best)
            self._save_unlocked(data)

        self._log_usage_event('account_rotated', provider, best.email, {
            'new_account_id': best.account_id,
            'messages_remaining': best.messages_remaining,
            'success_rate': best.success_rate,
        })
        logger.info(
            'account_ledger: rotated %s -> %s (%d msgs remaining)',
            provider, best.email, best.messages_remaining,
        )
        return best

    # ------------------------------------------------------------------
    # Registro de uso
    # ------------------------------------------------------------------

    def record_usage(
        self,
        provider: str,
        *,
        messages_used: int | None = None,
        messages_limit: int | None = None,
        reset_at: datetime | str | None = None,
        success: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> AccountEntry | None:
        """Registra uso de la cuenta activa. Si se agota, rota automaticamente."""
        provider = provider.strip().lower()

        with self._lock:
            data = self._load_unlocked()
            active_id = data.get('active_accounts', {}).get(provider)
            if not active_id:
                return None

            acct_dict = None
            acct_idx = -1
            for i, a in enumerate(data.get('accounts', [])):
                if a.get('account_id') == active_id:
                    acct_dict = a
                    acct_idx = i
                    break
            if acct_dict is None:
                return None

            acct = AccountEntry.from_dict(acct_dict)
            if messages_used is not None:
                acct.messages_used = messages_used
            if messages_limit is not None:
                acct.messages_limit = messages_limit
            if reset_at is not None:
                acct.reset_at = _coerce_dt(reset_at)
            acct.last_used = self._clock()
            acct.total_requests += 1
            if success:
                acct.successful_requests += 1
            if acct.total_requests > 0:
                acct.success_rate = acct.successful_requests / acct.total_requests

            data['accounts'][acct_idx] = acct.to_dict()
            self._save_unlocked(data)

        self._log_usage_event('usage_recorded', provider, acct.email, {
            'messages_used': acct.messages_used,
            'messages_limit': acct.messages_limit,
            'success': success,
            **(metadata or {}),
        })

        # Auto-rotacion si se agoto
        if acct.is_exhausted:
            logger.info(
                'account_ledger: %s/%s agotada (%d/%d). Rotando...',
                provider, acct.email, acct.messages_used, acct.messages_limit,
            )
            rotated = self.rotate_account(provider)
            if rotated:
                return rotated
            # Sin mas cuentas: sugerir fallback a local
            return acct

        return acct

    # ------------------------------------------------------------------
    # Proyeccion de agotamiento
    # ------------------------------------------------------------------

    def predict_exhaustion(self, provider: str) -> dict[str, Any]:
        """Proyecta cuando se agota la cuota de la cuenta activa.

        Retorna dict con:
        - estimated_exhaustion_at: datetime estimada
        - messages_remaining: int
        - usage_rate_per_hour: float
        - hours_until_exhaustion: float
        - should_rotate_soon: bool
        """
        acct = self.get_active_account(provider)
        if not acct:
            return {'error': 'no_active_account', 'provider': provider}

        if acct.messages_limit <= 0 or provider in self.LOCAL_PROVIDERS:
            return {
                'provider': provider,
                'unlimited': True,
                'messages_remaining': 999999,
                'should_rotate_soon': False,
            }

        now = self._clock()
        remaining = acct.messages_remaining
        usage_events = self._recent_usage_events(provider, hours=24)
        total_msgs_in_window = sum(e.get('messages_used', 0) for e in usage_events)
        hours_in_window = max(1.0, len(usage_events))

        if total_msgs_in_window > 0 and len(usage_events) > 1:
            first_ts = _coerce_dt(usage_events[0].get('timestamp', now))
            last_ts = _coerce_dt(usage_events[-1].get('timestamp', now))
            span_hours = max(0.1, (last_ts - first_ts).total_seconds() / 3600.0)
            usage_rate = total_msgs_in_window / span_hours
        else:
            usage_rate = 0.0

        if usage_rate > 0:
            hours_left = remaining / usage_rate
            exhaustion_at = now + timedelta(hours=hours_left)
        else:
            hours_left = float('inf')
            exhaustion_at = None

        should_rotate_soon = (
            remaining <= 5
            or (hours_left < 2.0 and remaining < 20)
        )

        return {
            'provider': provider,
            'email': acct.email,
            'messages_remaining': remaining,
            'messages_used': acct.messages_used,
            'messages_limit': acct.messages_limit,
            'reset_at': acct.reset_at.isoformat() if acct.reset_at else None,
            'usage_rate_per_hour': round(usage_rate, 2),
            'hours_until_exhaustion': round(hours_left, 2) if hours_left != float('inf') else None,
            'estimated_exhaustion_at': exhaustion_at.isoformat() if exhaustion_at else None,
            'should_rotate_soon': should_rotate_soon,
            'unlimited': False,
        }

    # ------------------------------------------------------------------
    # Resumen global
    # ------------------------------------------------------------------

    def account_summary(self) -> dict[str, Any]:
        """Estado de todas las cuentas, agrupadas por provider."""
        data = self._load()
        by_provider: dict[str, list[dict[str, Any]]] = {}
        active_accounts = data.get('active_accounts', {})

        for acct_dict in data.get('accounts', []):
            prov = acct_dict.get('provider', 'unknown')
            entry = AccountEntry.from_dict(acct_dict)
            is_active = active_accounts.get(prov) == entry.account_id
            info = {
                'account_id': entry.account_id,
                'email': entry.email,
                'status': entry.status,
                'is_active': is_active,
                'messages_used': entry.messages_used,
                'messages_limit': entry.messages_limit,
                'messages_remaining': entry.messages_remaining,
                'success_rate': round(entry.success_rate, 3),
                'reset_at': entry.reset_at.isoformat() if entry.reset_at else None,
                'last_used': entry.last_used.isoformat() if entry.last_used else None,
            }
            by_provider.setdefault(prov, []).append(info)

        providers_summary: dict[str, Any] = {}
        for prov, accounts in by_provider.items():
            total_remaining = sum(a['messages_remaining'] for a in accounts)
            active_list = [a for a in accounts if a['is_active']]
            providers_summary[prov] = {
                'total_accounts': len(accounts),
                'active_account': active_list[0] if active_list else None,
                'total_remaining_messages': total_remaining,
                'accounts': accounts,
            }

        return {
            'generated_at': self._clock().isoformat(),
            'total_accounts': sum(len(v) for v in by_provider.values()),
            'providers': providers_summary,
        }

    # ------------------------------------------------------------------
    # Diagnostico de fallos externos (aprendizaje del error 403 de Devin)
    # ------------------------------------------------------------------

    def record_external_tool_fault(
        self,
        provider: str,
        fault_type: str,
        *,
        diagnosis: str = '',
        our_credentials_ok: bool = True,
        external_service_fault: bool = False,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        """Registra un fallo de herramienta externa con diagnostico.

        Distingue entre:
        - Nuestras credenciales son invalidas -> accion: rotar token
        - Nuestras credenciales estan bien pero el servicio externo falla
          -> accion: ruta alternativa, no pedir al usuario que verifique
        """
        event = {
            'type': 'external_tool_fault',
            'provider': provider,
            'fault_type': fault_type,
            'diagnosis': diagnosis,
            'our_credentials_ok': our_credentials_ok,
            'external_service_fault': external_service_fault,
            'evidence': evidence or {},
            'timestamp': self._clock().isoformat(),
        }
        self._append_usage_log(event)
        logger.info(
            'account_ledger: external_tool_fault %s — %s (creds_ok=%s, ext_fault=%s)',
            provider, fault_type, our_credentials_ok, external_service_fault,
        )

    def get_fault_history(
        self,
        provider: str | None = None,
        *,
        hours: int = 168,
    ) -> list[dict[str, Any]]:
        """Retorna historial de fallos de herramientas externas."""
        cutoff = self._clock() - timedelta(hours=hours)
        events = self._read_usage_log()
        results: list[dict[str, Any]] = []
        for ev in events:
            if ev.get('type') != 'external_tool_fault':
                continue
            if provider and ev.get('provider') != provider:
                continue
            ts = _coerce_dt(ev.get('timestamp', ''))
            if ts >= cutoff:
                results.append(ev)
        return results

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _load(self) -> dict[str, Any]:
        try:
            if self._accounts_path.is_file():
                return json.loads(self._accounts_path.read_text(encoding='utf-8'))
        except Exception as exc:
            logger.warning('account_ledger: error loading %s: %s', self._accounts_path, exc)
        return {'accounts': [], 'active_accounts': {}}

    def _load_unlocked(self) -> dict[str, Any]:
        return self._load()

    def _save_unlocked(self, data: dict[str, Any]) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            self._accounts_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8',
            )
        except Exception as exc:
            logger.error('account_ledger: error saving %s: %s', self._accounts_path, exc)

    def _update_account_unlocked(self, data: dict[str, Any], acct: AccountEntry) -> None:
        for i, a in enumerate(data.get('accounts', [])):
            if a.get('account_id') == acct.account_id:
                data['accounts'][i] = acct.to_dict()
                return

    def _log_usage_event(self, event_type: str, provider: str, email: str, extra: dict[str, Any]) -> None:
        event = {
            'type': event_type,
            'provider': provider,
            'email': email,
            'timestamp': self._clock().isoformat(),
            **extra,
        }
        self._append_usage_log(event)

    def _append_usage_log(self, event: dict[str, Any]) -> None:
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            with self._usage_log_path.open('a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as exc:
            logger.warning('account_ledger: error appending usage log: %s', exc)

    def _read_usage_log(self) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        try:
            if not self._usage_log_path.is_file():
                return events
            for line in self._usage_log_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning('account_ledger: error reading usage log: %s', exc)
        return events

    def _recent_usage_events(
        self, provider: str, *, hours: int = 24,
    ) -> list[dict[str, Any]]:
        cutoff = self._clock() - timedelta(hours=hours)
        events = self._read_usage_log()
        results: list[dict[str, Any]] = []
        for ev in events:
            if ev.get('provider') != provider:
                continue
            if ev.get('type') != 'usage_recorded':
                continue
            ts = _coerce_dt(ev.get('timestamp', ''))
            if ts >= cutoff:
                results.append(ev)
        return results
