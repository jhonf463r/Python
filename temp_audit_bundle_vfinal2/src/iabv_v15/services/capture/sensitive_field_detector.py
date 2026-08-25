from __future__ import annotations

import re

from iabv_v15.domain.models import SensitiveFieldMatch, SitePolicy


class SensitiveFieldDetector:
    PASSWORD_WORDS = {"password", "passwd", "pwd", "pin", "passcode", "contrasena", "clave"}
    TOKEN_WORDS = {"token", "auth", "authorization", "bearer", "jwt", "csrf", "session", "cookie"}
    USER_WORDS = {"email", "mail", "user", "username", "login", "document", "documento", "correo", "usuario"}
    EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def classify(
        self,
        *,
        selector: str | None = None,
        field_name: str | None = None,
        input_type: str | None = None,
        autocomplete: str | None = None,
        label: str | None = None,
        header_name: str | None = None,
        value: str | None = None,
        site_policy: SitePolicy | None = None,
    ) -> SensitiveFieldMatch:
        reasons: list[str] = []
        role = 'generic'
        policy_source: str | None = None

        selector_value = (selector or '').lower()
        field_name_value = (field_name or '').lower()
        input_type_value = (input_type or '').lower()
        autocomplete_value = (autocomplete or '').lower()
        label_value = (label or '').lower()
        header_name_value = (header_name or '').lower()
        text_blob = ' '.join([selector_value, field_name_value, label_value]).strip()

        if input_type_value == 'password':
            reasons.append('password_input_type')
            role = 'password'
        if input_type_value == 'email':
            reasons.append('email_input_type')
            role = 'email'
        if any(token in autocomplete_value for token in {'password', 'current-password', 'new-password'}):
            reasons.append('password_autocomplete')
            role = 'password'
        if any(token in autocomplete_value for token in {'email', 'username'}):
            reasons.append('account_autocomplete')
            role = 'email' if 'email' in autocomplete_value or self._looks_like_email(value) else 'username'
        if self._contains_keywords(text_blob, self.PASSWORD_WORDS):
            reasons.append('password_keyword')
            role = 'password'
        if header_name_value in {'authorization', 'cookie', 'set-cookie'}:
            reasons.append('sensitive_header')
            role = 'token' if 'author' in header_name_value else 'cookie'
        if self._contains_keywords(' '.join([text_blob, header_name_value]), self.TOKEN_WORDS):
            reasons.append('token_keyword')
            role = 'token'
        if self._contains_keywords(text_blob, self.USER_WORDS):
            reasons.append('account_keyword')
            role = 'email' if 'email' in text_blob or 'correo' in text_blob or self._looks_like_email(value) else 'username'
        if value and self._looks_like_email(value):
            reasons.append('email_value')
            role = 'email'

        if site_policy is not None:
            policy_source = site_policy.site_id
            sensitive_selectors = [item.lower() for item in site_policy.sensitive_selectors]
            sensitive_names = [item.lower() for item in site_policy.sensitive_names]
            if selector_value and any(rule and (rule in selector_value or selector_value in rule) for rule in sensitive_selectors):
                reasons.append('policy_sensitive_selector')
            if field_name_value and any(rule and (rule == field_name_value or rule in field_name_value) for rule in sensitive_names):
                reasons.append('policy_sensitive_name')
            if header_name_value and any(rule and rule in header_name_value for rule in sensitive_names):
                reasons.append('policy_sensitive_header_name')
            if site_policy.redact_emails and value and self._looks_like_email(value):
                reasons.append('policy_email_redaction')
            if site_policy.redact_tokens and self._contains_keywords(' '.join([text_blob, header_name_value]), self.TOKEN_WORDS):
                reasons.append('policy_token_redaction')

        return SensitiveFieldMatch(
            sensitive=bool(reasons),
            field_role=role,
            reasons=reasons,
            value_length=len(value) if value is not None else None,
            policy_source=policy_source,
        )

    def _contains_keywords(self, text: str, keywords: set[str]) -> bool:
        text = text.lower()
        return any(keyword in text for keyword in keywords)

    def _looks_like_email(self, value: str | None) -> bool:
        if not value:
            return False
        return bool(self.EMAIL_RE.match(value.strip()))
