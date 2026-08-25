from __future__ import annotations

from iabv_v15.domain.models import BrowserObservationBundle, CaptureChannel, CapturedStep, DomSnapshot, RedactionSummary, SitePolicy
from iabv_v15.services.capture.browser_learning_assembler import BrowserLearningAssembler


def test_browser_learning_assembler_marks_login_ready_when_auth_flow_is_visible() -> None:
    assembler = BrowserLearningAssembler()
    site_policy = SitePolicy(site_id="wplay", display_name="Wplay", domains=["wplay.co"])
    steps = [
        CapturedStep(
            episode_id="ep-1",
            action_type="input",
            target="#login-username",
            screenshot_path="one.png",
            metadata={"capture_channel": CaptureChannel.VISIBLE.value, "field_role": "email", "selector": "#login-username", "element_rect": {"x": 40, "y": 80, "width": 280, "height": 44}, "viewport_width": 1280, "viewport_height": 720},
        ),
        CapturedStep(
            episode_id="ep-1",
            action_type="input",
            target="#login-password",
            screenshot_path="two.png",
            metadata={"capture_channel": CaptureChannel.VISIBLE.value, "field_role": "password", "selector": "#login-password", "sensitive": True, "element_rect": {"x": 40, "y": 142, "width": 280, "height": 44}, "viewport_width": 1280, "viewport_height": 720},
        ),
        CapturedStep(
            episode_id="ep-1",
            action_type="keydown",
            screenshot_path="two.png",
            target="#login-password",
            metadata={"capture_channel": CaptureChannel.VISIBLE.value, "field_role": "password", "key_display": "Enter", "selector": "#login-password", "element_rect": {"x": 40, "y": 142, "width": 280, "height": 44}, "viewport_width": 1280, "viewport_height": 720},
        ),
        CapturedStep(
            episode_id="ep-1",
            action_type="submit",
            screenshot_path="three.png",
            target="#login-form",
            metadata={"capture_channel": CaptureChannel.VISIBLE.value, "element_role": "form", "selector": "#login-form", "button_text": "Ingresar", "element_rect": {"x": 42, "y": 208, "width": 184, "height": 42}, "viewport_width": 1280, "viewport_height": 720},
        ),
    ]
    bundle = BrowserObservationBundle(
        episode_id="ep-1",
        url="https://wplay.co/login",
        capture_channels=[CaptureChannel.VISIBLE, CaptureChannel.BACKGROUND],
        dom_snapshots=[
            DomSnapshot(
                episode_id="ep-1",
                url="https://wplay.co/home",
                title="Mi cuenta",
                visible_text_excerpt="loggedInPlayer-recent balance disponible",
            )
        ],
        capture_stats={"status": "completed", "visible_step_count": 4, "screenshot_count": 2},
    )

    packet = assembler.assemble(
        episode_id="ep-1",
        site_policy=site_policy,
        steps=steps,
        artifacts=[],
        bundle=bundle,
        redaction_summary=RedactionSummary(),
    )

    assert packet["login_learning"]["status"] == "ready"
    assert packet["learning_readiness"]["status"] == "ready"
    assert packet["relevant_step_count"] >= 4
    assert any("iniciar sesion" in command.lower() for command in packet["suggested_commands"])
