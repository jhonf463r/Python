"""Tests for _replace_with_retry in storage.py."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

from iabv_v15.infra.persistence.storage import _replace_with_retry


@pytest.fixture()
def tmp_pair(tmp_path: Path):
    src = tmp_path / "src.json"
    dst = tmp_path / "dst.json"
    src.write_text('{"ok": true}', encoding="utf-8")
    return src, dst


def test_happy_path(tmp_pair):
    src, dst = tmp_pair
    _replace_with_retry(src, dst)
    assert dst.read_text(encoding="utf-8") == '{"ok": true}'
    assert not src.exists()


def test_retry_succeeds_on_second_attempt(tmp_pair):
    src, dst = tmp_pair
    call_count = 0
    orig = os.replace

    def flaky(s, d):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise PermissionError("[WinError 32] file in use")
        return orig(s, d)

    with mock.patch("iabv_v15.infra.persistence.storage._IS_WINDOWS", True), \
         mock.patch("iabv_v15.infra.persistence.storage._REPLACE_MAX_ATTEMPTS", 3), \
         mock.patch("iabv_v15.infra.persistence.storage._REPLACE_RETRY_DELAY", 0.001), \
         mock.patch("os.replace", side_effect=flaky):
        _replace_with_retry(src, dst)

    assert call_count == 2
    assert dst.read_text(encoding="utf-8") == '{"ok": true}'


def test_fallback_to_copy_on_exhausted_retries(tmp_pair):
    src, dst = tmp_pair

    def always_fail(s, d):
        raise PermissionError("[WinError 32] file in use")

    with mock.patch("iabv_v15.infra.persistence.storage._IS_WINDOWS", True), \
         mock.patch("iabv_v15.infra.persistence.storage._REPLACE_MAX_ATTEMPTS", 2), \
         mock.patch("iabv_v15.infra.persistence.storage._REPLACE_RETRY_DELAY", 0.001), \
         mock.patch("os.replace", side_effect=always_fail):
        _replace_with_retry(src, dst)

    assert dst.read_text(encoding="utf-8") == '{"ok": true}'


def test_raises_on_non_windows_permission_error(tmp_pair):
    src, dst = tmp_pair

    def fail(s, d):
        raise PermissionError("not windows")

    with mock.patch("iabv_v15.infra.persistence.storage._IS_WINDOWS", False), \
         mock.patch("os.replace", side_effect=fail):
        with pytest.raises(PermissionError):
            _replace_with_retry(src, dst)


def test_raises_on_non_permission_error(tmp_pair):
    src, dst = tmp_pair

    def fail(s, d):
        raise OSError("disk full")

    with mock.patch("os.replace", side_effect=fail):
        with pytest.raises(OSError, match="disk full"):
            _replace_with_retry(src, dst)


def test_artifact_storage_uses_retry(tmp_path):
    from iabv_v15.infra.persistence.storage import ArtifactStorage

    storage = ArtifactStorage(str(tmp_path))
    storage.save_json_atomic("data.json", {"hello": "world"})
    assert storage.load_json("data.json") == {"hello": "world"}
