from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any
from urllib.parse import unquote, urlparse

from iabv_v15.domain.models import CapturedStep, NetworkExchange, RedactionSummary, SitePolicy
from iabv_v15.services.capture.secret_vault import SecretVault
from iabv_v15.services.capture.sensitive_field_detector import SensitiveFieldDetector


class RedactionEngine:
    BODY_KEYS = {'password', 'passwd', 'pwd', 'token', 'authorization', 'cookie', 'csrf', 'email', 'username'}
    BEARER_RE = re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE)
    EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9.-]+\.[A-Za-z]{2,})')
    JSON_SECRET_RE = re.compile(
        r'(?P<prefix>"(?P<key>password|passwd|pwd|token|authorization|cookie|csrf|email|username)"\s*:\s*")(?P<value>[^"]*)(?P<suffix>")',
        re.IGNORECASE,
    )
    QUERY_SECRET_RE = re.compile(
        r'(?P<prefix>(?:^|[?&#;]|%26)(?P<key>password|passwd|pwd|token|authorization|cookie|csrf|email|username)(?:=|%3[Dd]))(?P<value>[^&#\s]*)',
        re.IGNORECASE,
    )
    MULTIPART_SECRET_RE = re.compile(
        r'(?P<header>name="(?P<key>password|passwd|pwd|token|authorization|cookie|csrf|email|username)"\r?\n\r?\n)(?P<value>.*?)(?=(?:\r?\n--|$))',
        re.IGNORECASE | re.S,
    )

    def __init__(self, detector: SensitiveFieldDetector, secret_vault: SecretVault | None = None) -> None:
        self.detector = detector
        self.secret_vault = secret_vault

    def redact_step(self, step: CapturedStep, site_policy: SitePolicy | None = None) -> tuple[CapturedStep, RedactionSummary]:
        metadata = deepcopy(step.metadata)
        sanitized_target = self.redact_free_text(step.target, site_policy=site_policy)
        for key in ('selector', 'url', 'frame_url', 'frame_selector', 'textPreview', 'button_text', 'aria_label', 'placeholder', 'name'):
            if isinstance(metadata.get(key), str):
                metadata[key] = self.redact_free_text(metadata.get(key), site_policy=site_policy)

        selector = metadata.get('selector') or sanitized_target
        field_name = metadata.get('name') or metadata.get('field_name')
        input_type = metadata.get('input_type') or metadata.get('field_type')
        autocomplete = metadata.get('autocomplete')
        label = metadata.get('label') or metadata.get('textPreview')
        url = metadata.get('url')
        domain = urlparse(url).netloc if url else metadata.get('domain', '')
        match = self.detector.classify(
            selector=selector,
            field_name=field_name,
            input_type=input_type,
            autocomplete=autocomplete,
            label=label,
            value=step.text_value,
            site_policy=site_policy,
        )
        summary = RedactionSummary()

        if not match.sensitive:
            metadata.setdefault('sensitive', False)
            return step.model_copy(update={'target': sanitized_target, 'metadata': metadata}), summary

        metadata.update(
            {
                'selector': selector,
                'sensitive': True,
                'field_role': match.field_role,
                'value_length': len(step.text_value) if step.text_value is not None else metadata.get('value_length'),
                'domain': domain,
                'sensitive_reasons': match.reasons,
            }
        )

        if step.text_value is None:
            return step.model_copy(update={'target': sanitized_target, 'metadata': metadata}), summary

        masked_value = self._mask_value(step.text_value, match.field_role)
        account = metadata.get('account_hint') or metadata.get('account') or ('user@' + domain if domain else 'site-user')
        vault_payload = None
        if self.secret_vault is not None:
            vault_reference = self.secret_vault.put_secret(domain or 'unknown.local', account, match.field_role, step.text_value)
            if vault_reference.available:
                vault_payload = vault_reference.model_dump(mode='json')
                summary.stored_secrets += 1
            else:
                summary.warnings.append('Secret vault unavailable; stored data remains masked only.')

        metadata.update(
            {
                'masked_value': masked_value,
                'vault_ref': vault_payload,
            }
        )
        summary.redacted_steps = 1
        redacted = step.model_copy(update={'target': sanitized_target, 'text_value': None, 'metadata': metadata})
        return redacted, summary

    def redact_network_exchange(
        self,
        exchange: NetworkExchange,
        site_policy: SitePolicy | None = None,
    ) -> tuple[NetworkExchange, RedactionSummary]:
        request_headers, request_count = self._redact_mapping(exchange.request_headers, site_policy=site_policy, treat_keys_as_headers=True)
        response_headers, response_count = self._redact_mapping(exchange.response_headers, site_policy=site_policy, treat_keys_as_headers=True)
        request_body, request_body_count = self._redact_text_or_json(exchange.request_body, site_policy=site_policy)
        response_body, response_body_count = self._redact_text_or_json(exchange.response_body, site_policy=site_policy)
        total = request_count + response_count + request_body_count + response_body_count
        redacted = exchange.model_copy(
            update={
                'request_headers': request_headers,
                'response_headers': response_headers,
                'request_body': request_body,
                'response_body': response_body,
                'redacted': total > 0,
            }
        )
        summary = RedactionSummary(redacted_network_fields=total)
        return redacted, summary

    def redact_free_text(self, text: str | None, *, site_policy: SitePolicy | None = None) -> str | None:
        if text is None:
            return None
        redacted_text = text
        for _ in range(2):
            redacted_text = self.BEARER_RE.sub('Bearer [REDACTED]', redacted_text)
            redacted_text = self._redact_json_pairs(redacted_text)
            redacted_text = self._redact_query_pairs(redacted_text)
            redacted_text = self._redact_multipart_pairs(redacted_text)
            if site_policy is None or site_policy.redact_emails:
                redacted_text, _ = self._mask_emails(redacted_text)
            decoded = unquote(redacted_text)
            if decoded == redacted_text:
                break
            redacted_text = decoded
        return redacted_text
    def _redact_mapping(
        self,
        values: dict[str, str],
        *,
        site_policy: SitePolicy | None = None,
        treat_keys_as_headers: bool = False,
    ) -> tuple[dict[str, str], int]:
        redacted: dict[str, str] = {}
        count = 0
        for key, value in values.items():
            match = self.detector.classify(
                field_name=key,
                header_name=key if treat_keys_as_headers else None,
                value=value,
                site_policy=site_policy,
            )
            if match.sensitive:
                redacted[key] = '[REDACTED]'
                count += 1
            else:
                redacted[key] = self.redact_free_text(value, site_policy=site_policy) or value
                if redacted[key] != value:
                    count += 1
        return redacted, count

    def _redact_text_or_json(self, value: str | None, *, site_policy: SitePolicy | None = None) -> tuple[str | None, int]:
        if value is None:
            return None, 0
        try:
            payload = json.loads(value)
        except Exception:
            redacted_text = self.redact_free_text(value, site_policy=site_policy) or value
            return redacted_text, 1 if redacted_text != value else 0

        redacted_payload, count = self._redact_json_value(payload, site_policy=site_policy)
        return json.dumps(redacted_payload, ensure_ascii=False), count

    def _redact_json_value(self, value: Any, *, key_hint: str | None = None, site_policy: SitePolicy | None = None) -> tuple[Any, int]:
        if isinstance(value, dict):
            output: dict[str, Any] = {}
            count = 0
            for key, item in value.items():
                match = self.detector.classify(field_name=key, value=str(item) if item is not None else None, site_policy=site_policy)
                if match.sensitive:
                    output[key] = '[REDACTED]'
                    count += 1
                else:
                    output[key], nested_count = self._redact_json_value(item, key_hint=key, site_policy=site_policy)
                    count += nested_count
            return output, count
        if isinstance(value, list):
            items = []
            count = 0
            for item in value:
                redacted_item, nested_count = self._redact_json_value(item, key_hint=key_hint, site_policy=site_policy)
                items.append(redacted_item)
                count += nested_count
            return items, count
        if isinstance(value, str):
            match = self.detector.classify(field_name=key_hint, value=value, site_policy=site_policy)
            if match.sensitive:
                return '[REDACTED]', 1
            redacted_text = self.redact_free_text(value, site_policy=site_policy) or value
            return redacted_text, 1 if redacted_text != value else 0
        return value, 0

    def _redact_json_pairs(self, text: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            key = (match.group('key') or '').lower()
            masked = self._mask_embedded_value(match.group('value') or '', key)
            return f"{match.group('prefix')}{masked}{match.group('suffix')}"

        return self.JSON_SECRET_RE.sub(_replace, text)

    def _redact_query_pairs(self, text: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            key = (match.group('key') or '').lower()
            masked = self._mask_embedded_value(match.group('value') or '', key)
            return f"{match.group('prefix')}{masked}"

        return self.QUERY_SECRET_RE.sub(_replace, text)

    def _redact_multipart_pairs(self, text: str) -> str:
        def _replace(match: re.Match[str]) -> str:
            key = (match.group('key') or '').lower()
            masked = self._mask_embedded_value((match.group('value') or '').strip(), key)
            return f"{match.group('header')}{masked}"

        return self.MULTIPART_SECRET_RE.sub(_replace, text)

    def _mask_embedded_value(self, value: str, key: str) -> str:
        if key in {'email', 'username'} and self._looks_like_email(value):
            return self._mask_email_value(value)
        return '[REDACTED]'

    def _mask_value(self, value: str, role: str) -> str:
        if role == 'email':
            return self._mask_email_value(value)
        if role == 'username':
            if len(value) <= 2:
                return '*' * len(value)
            return value[:1] + '***'
        return '[REDACTED]'

    def _mask_email_value(self, value: str) -> str:
        masked, count = self._mask_emails(value)
        return masked if count else '[REDACTED]'

    def _mask_emails(self, text: str) -> tuple[str, int]:
        count = 0

        def _replace(match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return f'{match.group(1)}***@{match.group(2)}'

        return self.EMAIL_RE.sub(_replace, text), count

    def _looks_like_email(self, value: str | None) -> bool:
        if not value:
            return False
        return bool(self.EMAIL_RE.search(value.strip()))

