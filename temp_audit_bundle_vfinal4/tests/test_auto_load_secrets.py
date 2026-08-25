"""Tests for _auto_load_secrets() in bootstrap.py."""
from __future__ import annotations

import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest


def _import_auto_load():
    from iabv_v15.bootstrap import _auto_load_secrets, _PS1_ENV_RE
    return _auto_load_secrets, _PS1_ENV_RE


class TestPS1EnvRegex:
    """Verify the regex matches valid PowerShell $env: assignments."""

    def test_single_quoted(self):
        _, regex = _import_auto_load()
        m = regex.match("$env:GITHUB_TOKEN_IABV = 'ghp_abc123'")
        assert m
        assert m.group(1) == 'GITHUB_TOKEN_IABV'
        assert m.group(2) == 'ghp_abc123'

    def test_double_quoted(self):
        _, regex = _import_auto_load()
        m = regex.match('$env:DEVIN_API_KEY = "cog_xyz789"')
        assert m
        assert m.group(1) == 'DEVIN_API_KEY'
        assert m.group(2) == 'cog_xyz789'

    def test_no_spaces(self):
        _, regex = _import_auto_load()
        m = regex.match("$env:FOO='bar'")
        assert m
        assert m.group(1) == 'FOO'
        assert m.group(2) == 'bar'

    def test_comment_not_matched(self):
        _, regex = _import_auto_load()
        m = regex.match("# $env:SECRET = 'value'")
        assert m is None

    def test_no_env_prefix(self):
        _, regex = _import_auto_load()
        m = regex.match("$FOO = 'bar'")
        assert m is None


class TestAutoLoadSecrets:
    """Verify _auto_load_secrets() injects env vars from ~/.iabv_secrets.ps1."""

    def _write_secrets_file(self, tmp_path: Path, content: str) -> Path:
        secrets_file = tmp_path / '.iabv_secrets.ps1'
        secrets_file.write_text(textwrap.dedent(content), encoding='utf-8')
        return secrets_file

    def test_loads_variables_when_file_exists(self, tmp_path: Path):
        auto_load, _ = _import_auto_load()
        self._write_secrets_file(tmp_path, """\
            # Secrets
            $env:TEST_TOKEN_A = 'value_a'
            $env:TEST_TOKEN_B = "value_b"
        """)
        env_backup = os.environ.copy()
        try:
            os.environ.pop('TEST_TOKEN_A', None)
            os.environ.pop('TEST_TOKEN_B', None)
            with patch('pathlib.Path.home', return_value=tmp_path):
                count = auto_load()
            assert count == 2
            assert os.environ['TEST_TOKEN_A'] == 'value_a'
            assert os.environ['TEST_TOKEN_B'] == 'value_b'
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_does_not_overwrite_existing(self, tmp_path: Path):
        auto_load, _ = _import_auto_load()
        self._write_secrets_file(tmp_path, """\
            $env:TEST_EXISTING = 'from_file'
        """)
        env_backup = os.environ.copy()
        try:
            os.environ['TEST_EXISTING'] = 'already_set'
            with patch('pathlib.Path.home', return_value=tmp_path):
                count = auto_load()
            assert count == 0
            assert os.environ['TEST_EXISTING'] == 'already_set'
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_overwrites_empty_existing(self, tmp_path: Path):
        auto_load, _ = _import_auto_load()
        self._write_secrets_file(tmp_path, """\
            $env:TEST_EMPTY = 'real_value'
        """)
        env_backup = os.environ.copy()
        try:
            os.environ['TEST_EMPTY'] = '   '
            with patch('pathlib.Path.home', return_value=tmp_path):
                count = auto_load()
            assert count == 1
            assert os.environ['TEST_EMPTY'] == 'real_value'
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_skips_placeholder_values(self, tmp_path: Path):
        auto_load, _ = _import_auto_load()
        self._write_secrets_file(tmp_path, """\
            $env:TEST_PLACEHOLDER = 'ghp_REEMPLAZAR_CON_PAT_REAL'
            $env:TEST_GOOD = 'actual_value'
        """)
        env_backup = os.environ.copy()
        try:
            os.environ.pop('TEST_PLACEHOLDER', None)
            os.environ.pop('TEST_GOOD', None)
            with patch('pathlib.Path.home', return_value=tmp_path):
                count = auto_load()
            assert count == 1
            assert 'TEST_PLACEHOLDER' not in os.environ
            assert os.environ['TEST_GOOD'] == 'actual_value'
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_returns_zero_when_no_file(self, tmp_path: Path):
        auto_load, _ = _import_auto_load()
        with patch('pathlib.Path.home', return_value=tmp_path):
            count = auto_load()
        assert count == 0

    def test_skips_comments_and_blanks(self, tmp_path: Path):
        auto_load, _ = _import_auto_load()
        self._write_secrets_file(tmp_path, """\
            # This is a comment
            
            # Another comment
            $env:TEST_ONLY = 'sole_value'
        """)
        env_backup = os.environ.copy()
        try:
            os.environ.pop('TEST_ONLY', None)
            with patch('pathlib.Path.home', return_value=tmp_path):
                count = auto_load()
            assert count == 1
            assert os.environ['TEST_ONLY'] == 'sole_value'
        finally:
            os.environ.clear()
            os.environ.update(env_backup)

    def test_handles_operational_flags(self, tmp_path: Path):
        """Verifies non-secret env flags (like IABV_AUTO_PROMOTION_PR_ENABLED) are also loaded."""
        auto_load, _ = _import_auto_load()
        self._write_secrets_file(tmp_path, """\
            $env:GITHUB_TOKEN_IABV = 'ghp_real_token'
            $env:DEVIN_API_KEY = 'cog_real_key'
            $env:IABV_AUTO_PROMOTION_PR_ENABLED = '1'
            $env:IABV_SYNAPTIC_ROUTING_ENABLED = '1'
        """)
        env_backup = os.environ.copy()
        try:
            for k in ('GITHUB_TOKEN_IABV', 'DEVIN_API_KEY',
                       'IABV_AUTO_PROMOTION_PR_ENABLED', 'IABV_SYNAPTIC_ROUTING_ENABLED'):
                os.environ.pop(k, None)
            with patch('pathlib.Path.home', return_value=tmp_path):
                count = auto_load()
            assert count == 4
            assert os.environ['GITHUB_TOKEN_IABV'] == 'ghp_real_token'
            assert os.environ['DEVIN_API_KEY'] == 'cog_real_key'
            assert os.environ['IABV_AUTO_PROMOTION_PR_ENABLED'] == '1'
            assert os.environ['IABV_SYNAPTIC_ROUTING_ENABLED'] == '1'
        finally:
            os.environ.clear()
            os.environ.update(env_backup)
