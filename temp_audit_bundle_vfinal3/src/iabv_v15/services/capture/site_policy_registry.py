from __future__ import annotations

from pathlib import Path

from iabv_v15.domain.models import SitePolicy


class SitePolicyRegistry:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def list_policies(self) -> list[SitePolicy]:
        policies = [SitePolicy.model_validate_json(path.read_text(encoding="utf-8")) for path in sorted(self.root_dir.glob("*.json"))]
        return sorted(policies, key=lambda policy: policy.display_name.lower())

    def get_policy(self, site_id: str) -> SitePolicy | None:
        path = self.root_dir / f"{site_id}.json"
        if not path.exists():
            return None
        return SitePolicy.model_validate_json(path.read_text(encoding="utf-8"))

    def upsert_policy(self, policy: SitePolicy) -> SitePolicy:
        path = self.root_dir / f"{policy.site_id}.json"
        path.write_text(policy.model_dump_json(indent=2), encoding="utf-8")
        return policy

    def _ensure_defaults(self) -> None:
        for policy in self._default_policies():
            path = self.root_dir / f"{policy.site_id}.json"
            if not path.exists():
                path.write_text(policy.model_dump_json(indent=2), encoding="utf-8")

    def _default_policies(self) -> list[SitePolicy]:
        return [
            SitePolicy(
                site_id="generic_web",
                display_name="Sitio web generico",
                domains=["*"],
                login_selector="input[type='password']",
                logout_selector="a[href*='logout'], button[aria-label*='logout']",
                username_selectors=[
                    "input[type='email']",
                    "input[name*='user']",
                    "input[name*='email']",
                ],
                sensitive_selectors=[
                    "input[type='password']",
                    "input[type='email']",
                    "input[name*='token']",
                ],
                sensitive_names=["password", "token", "authorization", "cookie", "email", "username"],
                notes="Politica base para entrenamiento web con proteccion de credenciales.",
            ),
            SitePolicy(
                site_id="wplay",
                display_name="Wplay",
                domains=["wplay.co"],
                login_selector="input[type='password']",
                logout_selector="a[href*='logout'], button[class*='logout'], [data-test*='logout']",
                username_selectors=[
                    "input[type='email']",
                    "input[name*='user']",
                    "input[name*='document']",
                ],
                sensitive_selectors=[
                    "input[type='password']",
                    "input[name*='password']",
                    "input[type='email']",
                    "input[name*='document']",
                ],
                sensitive_names=["email", "username", "documento", "password", "token", "session"],
                notes="Politica inicial para sesiones de login dinamico y aprendizaje seguro.",
            ),
        ]
