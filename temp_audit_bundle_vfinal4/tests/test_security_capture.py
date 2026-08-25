from __future__ import annotations

from iabv_v15.domain.models import CapturedStep, NetworkExchange, SecretReference, SitePolicy
from iabv_v15.services.capture.redaction_engine import RedactionEngine
from iabv_v15.services.capture.sensitive_field_detector import SensitiveFieldDetector


class DummyVault:
    @property
    def available(self) -> bool:
        return True

    def put_secret(self, domain: str, account: str, field_role: str, secret: str) -> SecretReference:
        return SecretReference(domain=domain, account=account, field_role=field_role, key=f'{domain}:{account}:{field_role}', available=True)


def test_redact_step_masks_password_and_creates_vault_reference() -> None:
    policy = SitePolicy(site_id='generic_web', display_name='Generico')
    engine = RedactionEngine(SensitiveFieldDetector(), DummyVault())
    step = CapturedStep(
        episode_id='ep-1',
        action_type='input',
        target='#password',
        text_value='Secreto123',
        metadata={'selector': '#password', 'name': 'password', 'input_type': 'password', 'url': 'https://site.test/login'},
    )
    redacted, summary = engine.redact_step(step, policy)
    assert redacted.text_value is None
    assert redacted.metadata['masked_value'] == '[REDACTED]'
    assert redacted.metadata['sensitive'] is True
    assert redacted.metadata['vault_ref']['field_role'] == 'password'
    assert summary.redacted_steps == 1
    assert summary.stored_secrets == 1


def test_redact_step_masks_email_and_keeps_only_masked_value() -> None:
    policy = SitePolicy(site_id='generic_web', display_name='Generico', sensitive_names=['Email'])
    engine = RedactionEngine(SensitiveFieldDetector(), DummyVault())
    step = CapturedStep(
        episode_id='ep-1',
        action_type='input',
        target='#user-email',
        text_value='demo@example.com',
        metadata={'selector': '#user-email', 'name': 'EMAIL', 'input_type': 'email', 'url': 'https://site.test/login'},
    )
    redacted, summary = engine.redact_step(step, policy)
    assert redacted.text_value is None
    assert redacted.metadata['field_role'] == 'email'
    assert redacted.metadata['masked_value'] == 'd***@example.com'
    assert 'demo@example.com' not in str(redacted.model_dump(mode='json'))
    assert summary.redacted_steps == 1
    assert summary.stored_secrets == 1


def test_redact_network_exchange_masks_headers_and_json_bodies() -> None:
    policy = SitePolicy(site_id='generic_web', display_name='Generico')
    engine = RedactionEngine(SensitiveFieldDetector(), DummyVault())
    exchange = NetworkExchange(
        episode_id='ep-1',
        url='https://site.test/graphql',
        method='POST',
        request_headers={'authorization': 'Bearer abc123', 'content-type': 'application/json'},
        response_headers={'set-cookie': 'session=abc'},
        request_body='{"email": "demo@example.com", "password": "123", "ok": true}',
        response_body='{"token": "abc", "status": "ok"}',
    )
    redacted, summary = engine.redact_network_exchange(exchange, policy)
    assert redacted.request_headers['authorization'] == '[REDACTED]'
    assert redacted.response_headers['set-cookie'] == '[REDACTED]'
    assert 'demo@example.com' not in (redacted.request_body or '')
    assert '123' not in (redacted.request_body or '')
    assert 'abc' not in (redacted.response_body or '')
    assert redacted.redacted is True
    assert summary.redacted_network_fields >= 4


def test_redact_step_sanitizes_frame_fallback_target_even_without_text_value() -> None:
    policy = SitePolicy(site_id='generic_web', display_name='Generico')
    engine = RedactionEngine(SensitiveFieldDetector(), DummyVault())
    step = CapturedStep(
        episode_id='ep-1',
        action_type='frame_fallback',
        target='https://example.com/frame#%7B%22requestType%22%3A%22LoginAndGetTempToken%22%2C%22postParams%22%3A%7B%22username%22%3A%22demo%40example.com%22%2C%22password%22%3A%22Secreto123%22%7D%7D',
        text_value=None,
        metadata={
            'selector': 'embedded_frame',
            'frame_url': 'https://example.com/frame#%7B%22requestType%22%3A%22LoginAndGetTempToken%22%2C%22postParams%22%3A%7B%22username%22%3A%22demo%40example.com%22%2C%22password%22%3A%22Secreto123%22%7D%7D',
            'name': 'password',
            'input_type': 'password',
            'url': 'https://site.test/login',
        },
    )

    redacted, summary = engine.redact_step(step, policy)

    serialized = str(redacted.model_dump(mode='json'))
    assert 'demo@example.com' not in serialized
    assert 'Secreto123' not in serialized
    assert '[REDACTED]' in serialized or 'd***@example.com' in serialized
    assert redacted.metadata['sensitive'] is True
    assert redacted.metadata['field_role'] == 'password'
    assert summary.redacted_steps == 0


def test_redact_network_exchange_masks_multipart_secrets() -> None:
    policy = SitePolicy(site_id='generic_web', display_name='Generico')
    engine = RedactionEngine(SensitiveFieldDetector(), DummyVault())
    body = (
        '--boundary\r\n'
        'Content-Disposition: form-data; name="email"\r\n\r\n'
        'demo@example.com\r\n'
        '--boundary\r\n'
        'Content-Disposition: form-data; name="token"\r\n\r\n'
        'super-secret-token\r\n'
        '--boundary--'
    )
    exchange = NetworkExchange(
        episode_id='ep-1',
        url='https://site.test/upload',
        method='POST',
        request_headers={'content-type': 'multipart/form-data; boundary=boundary'},
        request_body=body,
    )

    redacted, summary = engine.redact_network_exchange(exchange, policy)

    assert 'demo@example.com' not in (redacted.request_body or '')
    assert 'super-secret-token' not in (redacted.request_body or '')
    assert '[REDACTED]' in (redacted.request_body or '')
    assert summary.redacted_network_fields >= 1
