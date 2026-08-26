"""Detailed Groq provider audit - verify model, endpoint, and permissions."""
import os
import httpx
import json


def test_groq_detailed_audit():
    """Comprehensive Groq API audit to diagnose HTTP 404 model_not_found."""
    
    PROVIDER = 'groq'
    BASE_URL = 'https://api.groq.com/openai/v1'
    CHAT_ENDPOINT = '/chat/completions'
    MODELS_ENDPOINT = '/models'
    CONFIGURED_MODEL = 'llama-3.3-70b-versatile'
    
    api_key = os.environ.get('GROQ_API_KEY', '')
    API_KEY_PRESENT = bool(api_key)
    
    print("=" * 80)
    print("GROQ DETAILED AUDIT")
    print("=" * 80)
    print(f"PROVIDER = {PROVIDER}")
    print(f"BASE_URL = {BASE_URL}")
    print(f"CHAT_ENDPOINT = {CHAT_ENDPOINT}")
    print(f"MODELS_ENDPOINT = {MODELS_ENDPOINT}")
    print(f"CONFIGURED_MODEL = {CONFIGURED_MODEL}")
    print(f"API_KEY_PRESENT = {API_KEY_PRESENT}")
    print("=" * 80)
    
    if not API_KEY_PRESENT:
        print("API_KEY_ACCEPTED = N/A (no key)")
        print("REAL_PROVIDER_AVAILABLE = FALSE")
        return
    
    # Step 1: Query Groq Models API to verify model existence
    print("\n--- STEP 1: MODEL LOOKUP VIA MODELS API ---")
    models_url = f"{BASE_URL}{MODELS_ENDPOINT}"
    chat_url = f"{BASE_URL}{CHAT_ENDPOINT}"
    print(f"REQUEST_URL = {models_url}")
    print(f"HTTP_METHOD = GET")
    
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Say "test"'},
    ]
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                models_url,
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            )
            MODEL_LOOKUP_HTTP_STATUS = resp.status_code
            print(f"MODEL_LOOKUP_HTTP_STATUS = {MODEL_LOOKUP_HTTP_STATUS}")
            
            if resp.status_code == 200:
                models_data = resp.json()
                print(f"MODEL_LOOKUP_RESULT = SUCCESS")
                print(f"TOTAL_MODELS_AVAILABLE = {len(models_data.get('data', []))}")
                
                # Check if our model is in the list
                model_ids = [m['id'] for m in models_data.get('data', [])]
                print(f"CONFIGURED_MODEL_IN_LIST = {CONFIGURED_MODEL in model_ids}")
                
                if CONFIGURED_MODEL in model_ids:
                    print(f"MODEL_STATUS = EXISTS")
                    model_info = next(m for m in models_data.get('data', []) if m['id'] == CONFIGURED_MODEL)
                    print(f"MODEL_OWNED_BY = {model_info.get('owned_by', 'unknown')}")
                    print(f"MODEL_TYPE = {model_info.get('type', 'unknown')}")
                else:
                    print(f"MODEL_STATUS = NOT_FOUND_IN_LIST")
                    print(f"AVAILABLE_MODELS = {model_ids}")
                    print(f"TOTAL_MODELS_AVAILABLE = {len(model_ids)}")
                    
                    # Try to identify chat-capable models
                    print(f"\n--- TESTING AVAILABLE MODELS FOR CHAT COMPLETIONS ---")
                    for model_id in model_ids:
                        print(f"\nTesting model: {model_id}")
                        try:
                            with httpx.Client(timeout=30.0) as client:
                                resp = client.post(
                                    chat_url,
                                    json={'model': model_id, 'messages': messages, 'temperature': 0.15},
                                    headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                                )
                                print(f"  HTTP_STATUS = {resp.status_code}")
                                if resp.status_code == 200:
                                    print(f"  CHAT_CAPABLE = TRUE")
                                    print(f"  VALID_MODEL_FOUND = {model_id}")
                                    break
                                else:
                                    error_data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                                    print(f"  ERROR = {error_data.get('error', {}).get('code', 'unknown')}")
                        except Exception as e:
                            print(f"  EXCEPTION = {str(e)[:100]}")
            else:
                print(f"MODEL_LOOKUP_RESULT = FAILED")
                print(f"ERROR_BODY = {resp.text[:500]}")
    except Exception as exc:
        print(f"MODEL_LOOKUP_EXCEPTION = {type(exc).__name__}: {str(exc)[:200]}")
        MODEL_LOOKUP_HTTP_STATUS = 0
    
    # Step 2: Direct Chat Completions call with minimal request
    print("\n--- STEP 2: DIRECT CHAT COMPLETIONS CALL ---")
    print(f"REQUEST_URL = {chat_url}")
    print(f"HTTP_METHOD = POST")
    print(f"REQUEST_MODEL = {CONFIGURED_MODEL}")
    print(f"REQUEST_BODY = {{'model': '{CONFIGURED_MODEL}', 'messages': [...], 'temperature': 0.15}}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                chat_url,
                json={'model': CONFIGURED_MODEL, 'messages': messages, 'temperature': 0.15},
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            )
            CHAT_COMPLETION_HTTP_STATUS = resp.status_code
            print(f"CHAT_COMPLETION_HTTP_STATUS = {CHAT_COMPLETION_HTTP_STATUS}")
            
            if resp.status_code == 200:
                print(f"CHAT_COMPLETION_RESULT = SUCCESS")
                data = resp.json()
                print(f"RESPONSE_CLASS = {data.get('object', 'unknown')}")
                print(f"MODEL_USED = {data.get('model', 'unknown')}")
                print(f"API_KEY_ACCEPTED = TRUE")
                print(f"REAL_PROVIDER_AVAILABLE = TRUE")
            else:
                print(f"CHAT_COMPLETION_RESULT = FAILED")
                print(f"ERROR_TYPE = {resp.status_code}")
                error_data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                print(f"ERROR_MESSAGE = {error_data.get('error', {}).get('message', resp.text[:500])}")
                print(f"ERROR_CODE = {error_data.get('error', {}).get('code', 'unknown')}")
                
                # Distinguish error types
                error_code = error_data.get('error', {}).get('code', '')
                if error_code == 'model_not_found':
                    print(f"ERROR_CLASSIFICATION = MODEL_DOES_NOT_EXIST")
                elif error_code == 'invalid_request_error':
                    print(f"ERROR_CLASSIFICATION = INVALID_REQUEST")
                elif resp.status_code == 403:
                    print(f"ERROR_CLASSIFICATION = PERMISSION_DENIED")
                elif resp.status_code == 401:
                    print(f"ERROR_CLASSIFICATION = AUTHENTICATION_FAILED")
                else:
                    print(f"ERROR_CLASSIFICATION = UNKNOWN")
                
                print(f"API_KEY_ACCEPTED = UNKNOWN")
                print(f"REAL_PROVIDER_AVAILABLE = FALSE")
    except Exception as exc:
        print(f"CHAT_COMPLETION_EXCEPTION = {type(exc).__name__}: {str(exc)[:200]}")
        CHAT_COMPLETION_HTTP_STATUS = 0
        print(f"REAL_PROVIDER_AVAILABLE = FALSE")
    
    # Step 3: Check IABV model configuration source
    print("\n--- STEP 3: IABV MODEL CONFIGURATION SOURCE ---")
    print(f"CONFIG_SOURCE = HARDCODED_IN_CLOUD_REASONING_PLANNER")
    print(f"CONFIGURED_MODEL = {CONFIGURED_MODEL}")
    print(f"EFFECTIVE_MODEL = {CONFIGURED_MODEL}")
    print(f"FALLBACK_MODEL = None (no fallback configured)")
    
    # Step 4: Summary
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"PROVIDER = {PROVIDER}")
    print(f"BASE_URL = {BASE_URL}")
    print(f"EFFECTIVE_ENDPOINT = {CHAT_ENDPOINT}")
    print(f"CONFIGURED_MODEL = {CONFIGURED_MODEL}")
    print(f"EFFECTIVE_MODEL = {CONFIGURED_MODEL}")
    print(f"API_KEY_PRESENT = {API_KEY_PRESENT}")
    print(f"MODEL_LOOKUP_HTTP_STATUS = {MODEL_LOOKUP_HTTP_STATUS}")
    print(f"CHAT_COMPLETION_HTTP_STATUS = {CHAT_COMPLETION_HTTP_STATUS}")
    print("=" * 80)


if __name__ == '__main__':
    test_groq_detailed_audit()
