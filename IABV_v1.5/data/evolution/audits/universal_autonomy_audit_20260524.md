# Universal Autonomy Audit - 2026-05-24

## Scope

Audit focused on whether IABV can reason about its own environment, bind user language to visual/web targets, use external assistant surfaces without being limited to already-open windows, and feed failures back into metacognition.

## Evidence Read

- Runtime audit: `data/logs/runtime_audit.jsonl`
- Portable context: `data/evolution/portable_context/latest.json`
- Self examination: `data/evolution/self_examination/latest.json`
- World model: `data/evolution/world_model/latest.json`
- Platform pending: `data/evolution/platform_pending/*.json`

## Main Finding

IABV had enough evidence to know that the ChatGPT request was external, but it conflated two different states:

- visible target missing: no current ChatGPT window bound in WorldModel
- route incapable: no tool/session able to create an assistant surface

That produced a bad behavior: `chatgpt_web_assisted` was available, but visual calibration returned `target_unresolved`; the flow still waited about 50 seconds and returned a generic blocked message instead of explaining the true causal state.

## Fix Applied In This Slice

`ControlCenterViewModel` now distinguishes target visibility from route capability:

- If visual target is missing but the selected web-assisted route can create a surface, IABV proceeds and traces `external_target_missing_but_route_can_create_surface`.
- If visual target is missing and the route cannot create/open a surface, IABV blocks before clipboard/wait with `external_target_readiness_blocked`.
- Runtime `browser_security_verification` now opens the visible correct assistant path and explains that success requires `message_sent + response_captured`.

## Algorithmic Status

Working:

- `UniversalPerceptionService.resolve_visual_target_binding()` prevents Codex/IABV self-capture from being treated as ChatGPT.
- `UniversalPerceptionService.calibrate_visual_capabilities()` reports target binding, semantic reader availability, OCR status, score and unresolved fields.
- `UniversalPerceptionService.interpret_web_surface()` maps DOM/CDP/accessibility/OCR text into universal concepts such as `chat_input_ready`, `security_verification_candidate`, `authentication_required` and `ready_to_prompt`.
- OSES and PortableContext can surface repeated visual/communication gaps.

Still weak:

- Live semantic source acquisition is not complete. The concept resolver works when DOM/CDP/accessibility evidence is supplied, but live Windows runs still often have `semantic_reader_available=false`.
- The UI still needs a live proof showing `external_target_readiness_assessed -> route_can_create_surface -> response_captured` or a precise `browser_security_verification` handoff.
- Periodic idle self-tests are pending; the program records evidence, but does not yet run all calibration tests autonomously under an idle budget.

## Tests Run

- `tests/test_runtime_p044_visual_concept_resolver.py`: passed
- `tests/test_genesis_readiness_portable_context.py`: passed
- `tests/test_control_center_freeze_fix.py`: passed for the affected regression set
- `tests/test_portable_context_service.py`: passed
- `tests/test_operational_self_examination_service.py`: passed

Latest observed results:

- visual/genesis focused: `22 passed`
- control center visual/external regression: `108 passed`
- portable context + OSES regression: `43 passed`

## Next Live Proof

1. Restart IABV so the runtime loads this slice.
2. Ask: `haz una consulta en ChatGPT`.
3. Expected:
   - IABV should not fall to local chat.
   - If no visible ChatGPT window exists, it should use `chatgpt_web_assisted` because the route can create its own web surface.
   - If ChatGPT asks for security verification, IABV should open the correct visible path and ask for that human action.
   - It must not declare success until it proves message sent and response captured.

## UNRESOLVED

- `live_chatgpt_response_captured_after_target_readiness_gate`
- `live_semantic_reader_available_for_chatgpt_surface`
- `idle_self_tests_for_visual_grounding_and_web_surface_readiness`
- `cross_device_genesis_readiness_trial`
