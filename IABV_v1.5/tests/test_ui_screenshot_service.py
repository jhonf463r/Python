"""Tests backend de `UIScreenshotService`.

AGENTS.md: backend pytest ONLY, sin UI testing.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from iabv_v15.services.capture.ui_screenshot_service import (
    CompositeUIScreenshotProvider,
    NoopUIScreenshotProvider,
    PILUIScreenshotProvider,
    QtUIScreenshotProvider,
    UIScreenshotRecord,
    UIScreenshotService,
    _probe_png_dimensions,
    build_default_provider,
)


class _FailingProvider:
    def capture_to(self, path: Path) -> bool:
        return False


class _RaisingProvider:
    def capture_to(self, path: Path) -> bool:
        raise RuntimeError("boom")


class _FixedClock:
    def __init__(self, start: float = 1000.0, step: float = 1.0) -> None:
        self._now = float(start)
        self._step = float(step)

    def __call__(self) -> float:
        value = self._now
        self._now += self._step
        return value


def _new_service(tmp_path: Path, *, retention: int = 50, provider=None, clock=None) -> UIScreenshotService:
    return UIScreenshotService(
        storage_dir=tmp_path,
        provider=provider or NoopUIScreenshotProvider(),
        clock=clock or _FixedClock(),
        retention=retention,
    )


def test_noop_provider_writes_png_and_service_indexes_record(tmp_path: Path) -> None:
    service = _new_service(tmp_path)
    record = service.capture(source="manual", scope={"surface": "evolution_center"})
    assert isinstance(record, UIScreenshotRecord)
    assert record.success is True
    assert record.source == "manual"
    assert record.scope == {"surface": "evolution_center"}
    assert record.path.endswith(f"{record.record_id}.png")
    assert Path(record.path).exists()
    assert record.width == 1
    assert record.height == 1
    assert len(record.sha256) == 64

    index_path = tmp_path / "index.json"
    assert index_path.exists()
    index = json.loads(index_path.read_text())
    assert len(index) == 1
    assert index[0]["record_id"] == record.record_id


def test_capture_never_raises_when_provider_fails(tmp_path: Path) -> None:
    service = _new_service(tmp_path, provider=_FailingProvider())
    record = service.capture(source="on_failure")
    assert record.success is False
    assert record.sha256 == ""
    assert record.width == 0
    assert record.height == 0
    # El index igual se actualiza para trazabilidad.
    assert len(service.list_recent()) == 1


def test_capture_never_raises_when_provider_explodes(tmp_path: Path) -> None:
    service = _new_service(tmp_path, provider=_RaisingProvider())
    record = service.capture(source="resilience")
    assert record.success is False
    assert len(service.list_recent()) == 1


def test_list_recent_orders_by_created_at_epoch_descending(tmp_path: Path) -> None:
    service = _new_service(tmp_path, clock=_FixedClock(start=1.0, step=1.0))
    r1 = service.capture(source="a")
    r2 = service.capture(source="b")
    r3 = service.capture(source="c")

    recent = service.list_recent(limit=5)
    assert [r.record_id for r in recent] == [r3.record_id, r2.record_id, r1.record_id]

    limited = service.list_recent(limit=2)
    assert [r.record_id for r in limited] == [r3.record_id, r2.record_id]


def test_get_returns_record_by_id(tmp_path: Path) -> None:
    service = _new_service(tmp_path)
    r = service.capture(source="lookup")
    assert service.get(r.record_id) == r
    assert service.get("does-not-exist") is None


def test_retention_prunes_oldest_files_and_entries(tmp_path: Path) -> None:
    service = _new_service(tmp_path, retention=3, clock=_FixedClock(start=1.0, step=1.0))
    recs = [service.capture(source=f"r{i}") for i in range(5)]

    remaining = service.list_recent(limit=10)
    assert len(remaining) == 3
    remaining_ids = {r.record_id for r in remaining}
    # Los 3 mas nuevos deben quedar; los 2 mas viejos borrados (file + index).
    assert remaining_ids == {recs[-1].record_id, recs[-2].record_id, recs[-3].record_id}

    for old in recs[:2]:
        assert Path(old.path).exists() is False
    for kept in recs[-3:]:
        assert Path(kept.path).exists() is True


def test_composite_provider_tries_until_one_succeeds(tmp_path: Path) -> None:
    target = tmp_path / "out.png"
    composite = CompositeUIScreenshotProvider(
        providers=[_FailingProvider(), _RaisingProvider(), NoopUIScreenshotProvider()]
    )
    assert composite.capture_to(target) is True
    assert target.exists()


def test_composite_provider_returns_false_when_all_fail(tmp_path: Path) -> None:
    target = tmp_path / "out.png"
    composite = CompositeUIScreenshotProvider(providers=[_FailingProvider(), _RaisingProvider()])
    assert composite.capture_to(target) is False
    assert target.exists() is False


def test_build_default_provider_has_known_order() -> None:
    provider = build_default_provider()
    assert isinstance(provider, CompositeUIScreenshotProvider)
    kinds = [type(p).__name__ for p in provider.providers]
    assert kinds == [
        PILUIScreenshotProvider.__name__,
        QtUIScreenshotProvider.__name__,
        NoopUIScreenshotProvider.__name__,
    ]


def test_probe_png_dimensions_rejects_non_png_data() -> None:
    assert _probe_png_dimensions(b"") == (0, 0)
    assert _probe_png_dimensions(b"not a png" * 4) == (0, 0)


def test_index_survives_corruption(tmp_path: Path) -> None:
    service = _new_service(tmp_path)
    r = service.capture(source="ok")
    assert Path(r.path).exists()
    # Corrompemos el index; el servicio lo reconstruye al siguiente capture.
    (tmp_path / "index.json").write_text("{not json", encoding="utf-8")
    r2 = service.capture(source="recovery")
    assert service.get(r2.record_id) is not None
    # El record viejo se pierde del index pero no rompimos el servicio.
    assert service.get(r.record_id) is None


def test_record_as_dict_is_json_round_trippable(tmp_path: Path) -> None:
    service = _new_service(tmp_path)
    r = service.capture(source="x", scope={"a": "1"})
    payload = r.as_dict()
    serialized = json.dumps(payload)
    decoded = json.loads(serialized)
    assert decoded["record_id"] == r.record_id
    assert decoded["scope"] == {"a": "1"}
