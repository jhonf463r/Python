"""Tests para AccountLedgerService."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from iabv_v15.services.evolution.account_ledger_service import (
    AccountEntry,
    AccountLedgerService,
)


def _utc_now():
    return datetime.now(timezone.utc)


@pytest.fixture
def tmp_workspace(tmp_path: Path) -> Path:
    return tmp_path


@pytest.fixture
def ledger(tmp_workspace: Path) -> AccountLedgerService:
    return AccountLedgerService(tmp_workspace)


class TestAccountEntry:
    def test_create_default(self):
        entry = AccountEntry(provider='chatgpt', email='u@mail.com', credential_ref='$env:KEY')
        assert entry.provider == 'chatgpt'
        assert entry.email == 'u@mail.com'
        assert entry.status == 'active'
        assert entry.messages_used == 0
        assert entry.success_rate == 1.0

    def test_is_exhausted(self):
        entry = AccountEntry(provider='chatgpt', email='u@mail.com', credential_ref='ref',
                             messages_used=50, messages_limit=50)
        assert entry.is_exhausted is True

    def test_not_exhausted_no_limit(self):
        entry = AccountEntry(provider='ollama', email='local', credential_ref='ref',
                             messages_used=100, messages_limit=0)
        assert entry.is_exhausted is False

    def test_quota_fraction(self):
        entry = AccountEntry(provider='chatgpt', email='u@mail.com', credential_ref='ref',
                             messages_used=25, messages_limit=100)
        assert entry.quota_fraction == 0.75

    def test_roundtrip_dict(self):
        entry = AccountEntry(provider='claude', email='a@b.com', credential_ref='$env:CL',
                             messages_used=10, messages_limit=100)
        d = entry.to_dict()
        restored = AccountEntry.from_dict(d)
        assert restored.provider == 'claude'
        assert restored.messages_used == 10
        assert restored.account_id == entry.account_id


class TestAccountLedgerService:
    def test_register_and_get(self, ledger: AccountLedgerService):
        acct = ledger.register_account('chatgpt', 'user@mail.com', '$env:CHATGPT_KEY')
        assert acct.provider == 'chatgpt'

        active = ledger.get_active_account('chatgpt')
        assert active is not None
        assert active.email == 'user@mail.com'

    def test_upsert_existing(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'user@mail.com', '$env:KEY1', messages_limit=50)
        ledger.register_account('chatgpt', 'user@mail.com', '$env:KEY2', messages_limit=100)

        accounts = ledger.get_available_accounts('chatgpt')
        assert len(accounts) == 1
        assert accounts[0].messages_limit == 100

    def test_multiple_accounts(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@mail.com', '$env:K1', messages_limit=50)
        ledger.register_account('chatgpt', 'b@mail.com', '$env:K2', messages_limit=100)

        accounts = ledger.get_available_accounts('chatgpt')
        assert len(accounts) == 2

    def test_rotation(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@mail.com', '$env:K1',
                                messages_limit=50)
        ledger.register_account('chatgpt', 'b@mail.com', '$env:K2',
                                messages_limit=100)

        # Agotar la primera
        ledger.record_usage('chatgpt', messages_used=50, messages_limit=50)

        # Rotar
        new = ledger.rotate_account('chatgpt')
        assert new is not None
        assert new.email == 'b@mail.com'

    def test_rotation_no_more_accounts(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@mail.com', '$env:K1',
                                messages_limit=10)
        # Agotar
        ledger.record_usage('chatgpt', messages_used=10, messages_limit=10)

        result = ledger.rotate_account('chatgpt')
        assert result is None

    def test_record_usage_auto_rotates(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@mail.com', '$env:K1', messages_limit=10)
        ledger.register_account('chatgpt', 'b@mail.com', '$env:K2', messages_limit=100)

        result = ledger.record_usage('chatgpt', messages_used=10, messages_limit=10)
        assert result is not None
        # Debio rotar automaticamente
        active = ledger.get_active_account('chatgpt')
        assert active is not None
        assert active.email == 'b@mail.com'

    def test_predict_exhaustion(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@mail.com', '$env:K1', messages_limit=100)
        ledger.record_usage('chatgpt', messages_used=90, messages_limit=100)

        pred = ledger.predict_exhaustion('chatgpt')
        assert pred.get('messages_remaining') == 10
        assert pred.get('should_rotate_soon') is True

    def test_predict_exhaustion_unlimited(self, ledger: AccountLedgerService):
        ledger.register_account('ollama', 'local', '$env:NONE')
        pred = ledger.predict_exhaustion('ollama')
        assert pred.get('unlimited') is True

    def test_account_summary(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@m.com', '$env:K1', messages_limit=50)
        ledger.register_account('claude', 'b@m.com', '$env:K2', messages_limit=100)

        summary = ledger.account_summary()
        assert summary['total_accounts'] == 2
        assert 'chatgpt' in summary['providers']
        assert 'claude' in summary['providers']

    def test_unregister(self, ledger: AccountLedgerService):
        ledger.register_account('chatgpt', 'a@mail.com', '$env:K1')
        assert ledger.unregister_account('chatgpt', 'a@mail.com') is True
        assert ledger.get_active_account('chatgpt') is None

    def test_record_external_tool_fault(self, ledger: AccountLedgerService):
        ledger.record_external_tool_fault(
            'devin_proxy', '403_forbidden',
            diagnosis='Proxy returns 403 but GitHub API works with same token',
            our_credentials_ok=True,
            external_service_fault=True,
            evidence={'http_code': 403, 'proxy': 'git-manager.devin.ai'},
        )
        faults = ledger.get_fault_history('devin_proxy')
        assert len(faults) == 1
        assert faults[0]['our_credentials_ok'] is True
        assert faults[0]['external_service_fault'] is True

    def test_persistence(self, tmp_workspace: Path):
        ledger1 = AccountLedgerService(tmp_workspace)
        ledger1.register_account('chatgpt', 'a@mail.com', '$env:K1', messages_limit=50)
        ledger1.record_usage('chatgpt', messages_used=20, messages_limit=50)

        # Nuevo instance (simula restart)
        ledger2 = AccountLedgerService(tmp_workspace)
        active = ledger2.get_active_account('chatgpt')
        assert active is not None
        assert active.messages_used == 20

    def test_usage_log_written(self, ledger: AccountLedgerService, tmp_workspace: Path):
        ledger.register_account('chatgpt', 'a@m.com', '$env:K1')
        log_path = tmp_workspace / 'data' / 'evolution' / 'account_ledger' / 'usage_log.jsonl'
        assert log_path.is_file()
        lines = log_path.read_text(encoding='utf-8').strip().split('\n')
        assert len(lines) >= 1
        event = json.loads(lines[0])
        assert event['type'] == 'account_registered'
