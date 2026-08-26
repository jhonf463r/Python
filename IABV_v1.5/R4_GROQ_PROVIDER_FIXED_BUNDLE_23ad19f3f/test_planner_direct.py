"""Direct test of CloudReasoningPlannerService with new Groq model."""
import os
import httpx
from iabv_v15.services.adaptive.cloud_reasoning_planner import CloudReasoningPlannerService


def test_planner_direct():
    """Test CloudReasoningPlannerService directly with new Groq model."""
    
    # Check API key
    api_key = os.environ.get('GROQ_API_KEY', '')
    print(f"GROQ_API_KEY_PRESENT = {bool(api_key)}")
    
    if not api_key:
        print("NO API KEY - skipping test")
        return
    
    # First, test direct Groq call to see raw response
    print("\n--- DIRECT GROQ CALL TEST ---")
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Say "test"'},
    ]
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                'https://api.groq.com/openai/v1/chat/completions',
                json={'model': 'qwen/qwen3.6-27b', 'messages': messages, 'temperature': 0.15},
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            )
            print(f"HTTP_STATUS = {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                print(f"RESPONSE_CONTENT = {content[:500]}")
            else:
                print(f"ERROR = {resp.text[:500]}")
    except Exception as exc:
        print(f"EXCEPTION = {type(exc).__name__}: {str(exc)}")
    
    # Now test planner with detailed logging
    print("\n--- PLANNER TEST WITH DETAILED LOGGING ---")
    
    # Monkey-patch _extract_json to see what's happening
    original_extract_json = CloudReasoningPlannerService._extract_json
    
    def debug_extract_json(data, source):
        print(f"\n_EXTRACT_JSON CALLED (source={source})")
        print(f"RAW_DATA_KEYS = {list(data.keys())}")
        if 'choices' in data and len(data['choices']) > 0:
            raw_content = data['choices'][0]['message']['content']
            print(f"RAW_CONTENT_LENGTH = {len(raw_content)}")
            print(f"RAW_CONTENT_FULL = {raw_content}")
        result = original_extract_json(data, source)
        print(f"EXTRACT_RESULT = {result is not None}")
        if result is None:
            print("EXTRACT_FAILED = True")
        return result
    
    CloudReasoningPlannerService._extract_json = staticmethod(debug_extract_json)
    
    planner = CloudReasoningPlannerService()
    
    # Try to generate a plan
    user_goal = "create a test file to verify G1 execution"
    print(f"USER_GOAL = {user_goal}")
    
    try:
        plan = planner.generate_plan(user_goal)
        
        if plan is None:
            print("\nPLAN_GENERATION = FAILED (returned None)")
            print(f"API_HEALTH = {CloudReasoningPlannerService.get_api_health()}")
        else:
            print("\nPLAN_GENERATION = SUCCESS")
            print(f"PLAN_ID = {plan.plan_id}")
            print(f"SUMMARY = {plan.summary}")
            print(f"CONFIDENCE = {plan.confidence}")
            print(f"STEPS_COUNT = {len(plan.steps)}")
            if plan.steps:
                first_step = plan.steps[0]
                print(f"ASSIGNED_TOOL = {first_step.assigned_tool}")
                print(f"TOOL_RATIONALE = {first_step.tool_rationale}")
    except Exception as exc:
        print(f"\nPLAN_GENERATION = EXCEPTION: {type(exc).__name__}: {str(exc)}")
        import traceback
        traceback.print_exc()
        print(f"API_HEALTH = {CloudReasoningPlannerService.get_api_health()}")


if __name__ == '__main__':
    test_planner_direct()
