"""Tests for _replace_with_retry (Windows file-locking workaround)."""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from iabv_v15.infra.persistence.storage import (
    ArtifactStorage,
    _replace_with_retry,
)


def test_replace_with_retry_succeeds_first_try(tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("hello")
    _replace_with_retry(src, dst)
    assert dst.read_text() == "hello"
    assert not src.exists()


def test_replace_with_retry_retries_on_windows_permission_error(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("data")
    call_count = 0
    original_replace = os.replace

    def flaky_replace(s, d):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise PermissionError("[WinError 32] file locked")
        original_replace(s, d)

    with patch("iabv_v15.infra.persistence.storage._IS_WINDOWS", True), \
         patch("iabv_v15.infra.persistence.storage._REPLACE_MAX_ATTEMPTS", 5), \
         patch("iabv_v15.infra.persistence.storage._REPLACE_RETRY_DELAY", 0.01), \
         patch("os.replace", side_effect=flaky_replace):
        _replace_with_retry(src, dst)

    assert call_count == 3
    assert dst.read_text() == "data"


def test_replace_with_retry_falls_back_to_copy_on_exhausted_retries(
    tmp_path: Path,
) -> None:
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("fallback")

    with patch("iabv_v15.infra.persistence.storage._IS_WINDOWS", True), \
         patch("iabv_v15.infra.persistence.storage._REPLACE_MAX_ATTEMPTS", 2), \
         patch("iabv_v15.infra.persistence.storage._REPLACE_RETRY_DELAY", 0.01), \
         patch("os.replace", side_effect=PermissionError("[WinError 32]")):
        _replace_with_retry(src, dst)

    assert dst.read_text() == "fallback"


def test_replace_with_retry_raises_on_non_windows(tmp_path: Path) -> None:
    src = tmp_path / "src.txt"
    dst = tmp_path / "dst.txt"
    src.write_text("x")

    with patch("iabv_v15.infra.persistence.storage._IS_WINDOWS", False), \
         patch("os.replace", side_effect=PermissionError("denied")):
        with pytest.raises(PermissionError):
            _replace_with_retry(src, dst)


def test_save_json_atomic_uses_retry(tmp_path: Path) -> None:
    storage = ArtifactStorage(str(tmp_path))
    path = storage.save_json_atomic("test/card.json", {"key": "value"})
    assert Path(path).exists()
    loaded = storage.load_json("test/card.json")
    assert loaded == {"key": "value"}


def test_save_bytes_uses_retry(tmp_path: Path) -> None:
    storage = ArtifactStorage(str(tmp_path))
    path = storage.save_bytes("test/data.bin", b"binary")
    assert Path(path).exists()
    assert storage.load_bytes("test/data.bin") == b"binary"
