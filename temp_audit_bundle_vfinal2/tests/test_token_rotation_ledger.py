"""Tests focalizados para TokenRotationLedger (capa 2.2).

Cubren:
- append-only + persistencia round-trip
- deteccion implicita de rotacion (probe_failed -> probe_ok)
- ``prediction``: stale, expired_live, proactive_due, avg_interval_days
- ``predictions`` multi-token
- resiliencia frente a ledger corrupto / inexistente
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from iabv_v15.services.evolution.token_rotation_ledger import (
    TokenRotationLedger,
)


def _clock_at(ts: datetime):
    # Clock mutable via lista: permite avanzar el "now" entre registros.
    holder = {'now': ts}

    def _fn() -> datetime:
        return holder['now']

    return _fn, holder


def test_record_probe_persists_and_round_trips(tmp_path: Path) -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    clock, _ = _clock_at(now)
    ledger = TokenRotationLedger(tmp_path, clock=clock)
    ledger.record_probe('github_api', ok=True)
    ledger.record_probe('devin_api', ok=False, reason='401 Unauthorized')

    # Reinstanciamos para forzar round-trip desde disco.
    ledger2 = TokenRotationLedger(tmp_path, clock=clock)
    events = ledger2.events()
    kinds = [(ev['token_name'], ev['kind']) for ev in events]
    assert ('github_api', 'probe_ok') in kinds
    assert ('devin_api', 'probe_failed') in kinds


def test_implicit_rotation_inserted_between_failed_and_ok(tmp_path: Path) -> None:
    base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    clock, holder = _clock_at(base)
    ledger = TokenRotationLedger(tmp_path, clock=clock)

    ledger.record_probe('github_api', ok=True)
    holder['now'] = base + timedelta(days=28)
    ledger.record_probe('github_api', ok=False, reason='401')
    holder['now'] = base + timedelta(days=28, hours=1)
    # El usuario corrio rotate_tokens.ps1 en el medio; no tocamos el
    # ledger explicitamente — el siguiente probe_ok debe marcar rotacion.
    ledger.record_probe('github_api', ok=True)

    kinds = [ev['kind'] for ev in ledger.events('github_api')]
    # probe_ok -> probe_failed -> rotated (implicito) -> probe_ok
    assert kinds == ['probe_ok', 'probe_failed', 'rotated', 'probe_ok']


def test_prediction_marks_expired_live_when_last_is_failed(tmp_path: Path) -> None:
    base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    clock, holder = _clock_at(base)
    ledger = TokenRotationLedger(tmp_path, clock=clock)
    ledger.record_probe('github_api', ok=True)
    holder['now'] = base + timedelta(days=28)
    ledger.record_probe('github_api', ok=False, reason='401')

    holder['now'] = base + timedelta(days=28, minutes=5)
    pred = ledger.prediction('github_api')
    assert pred is not None
    assert pred['expired_live'] is True
    # El ultimo probe OK es de hace 28 dias; eso supera el STALE_THRESHOLD
    # (36h) asi que tambien es stale. OSES prioriza ``expired_live`` sobre
    # ``stale`` al construir el finding — eso se valida en el test de OSES.
    assert pred['stale'] is True


def test_prediction_marks_stale_when_no_recent_ok(tmp_path: Path) -> None:
    base = datetime(2026, 4, 1, 12, 0, tzinfo=timezone.utc)
    clock, holder = _clock_at(base)
    ledger = TokenRotationLedger(tmp_path, clock=clock)
    ledger.record_probe('github_api', ok=True)

    # Avanzamos el reloj mas alla del STALE_THRESHOLD (36h) sin nuevos probes.
    holder['now'] = base + timedelta(hours=48)
    pred = ledger.prediction('github_api')
    assert pred is not None
    assert pred['stale'] is True
    assert pred['expired_live'] is False


def test_prediction_projects_expiry_after_two_rotations(tmp_path: Path) -> None:
    base = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    clock, holder = _clock_at(base)
    ledger = TokenRotationLedger(tmp_path, clock=clock)

    # Patron: cada 30 dias el token expira y se rota. Dos ciclos completos.
    ledger.record_probe('github_api', ok=True)
    holder['now'] = base + timedelta(days=30)
    ledger.record_probe('github_api', ok=False, reason='401')
    holder['now'] = base + timedelta(days=30, hours=1)
    ledger.record_probe('github_api', ok=True)  # -> inserta rotated

    holder['now'] = base + timedelta(days=60)
    ledger.record_probe('github_api', ok=False, reason='401')
    holder['now'] = base + timedelta(days=60, hours=1)
    ledger.record_probe('github_api', ok=True)  # -> inserta rotated

    holder['now'] = base + timedelta(days=89)  # un dia antes del tercer expiry
    pred = ledger.prediction('github_api')
    assert pred is not None
    assert pred['rotations_observed'] == 2
    assert pred['avg_interval_days'] is not None
    assert 29.0 <= pred['avg_interval_days'] <= 31.0
    assert pred['proactive_due'] is True  # 30 dias desde ultima rotacion
    days_left = pred['days_until_projected_expiry']
    assert days_left is not None
    assert -1.0 <= days_left <= 2.0


def test_predictions_returns_entry_per_tracked_token(tmp_path: Path) -> None:
    now = datetime(2026, 4, 21, 12, 0, tzinfo=timezone.utc)
    clock, _ = _clock_at(now)
    ledger = TokenRotationLedger(tmp_path, clock=clock)
    ledger.record_probe('github_api', ok=True)
    ledger.record_probe('devin_api', ok=True)

    preds = ledger.predictions()
    names = {p['token_name'] for p in preds}
    assert names == {'github_api', 'devin_api'}


def test_load_is_resilient_to_corrupt_json(tmp_path: Path) -> None:
    root = tmp_path / 'data' / 'evolution' / 'token_rotations'
    root.mkdir(parents=True)
    (root / 'latest.json').write_text('{not valid json', encoding='utf-8')
    ledger = TokenRotationLedger(tmp_path)
    # No explota y se comporta como ledger vacio.
    assert ledger.tracked_tokens() == []
    assert ledger.events() == []
    # Nuevo probe arma estructura limpia.
    ledger.record_probe('github_api', ok=True)
    assert ledger.tracked_tokens() == ['github_api']


def test_prediction_without_events_is_none(tmp_path: Path) -> None:
    ledger = TokenRotationLedger(tmp_path)
    assert ledger.prediction('github_api') is None
    assert ledger.predictions() == []
