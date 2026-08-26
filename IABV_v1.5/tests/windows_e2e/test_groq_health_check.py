"""Direct Groq API health check - no mocks, real provider verification."""
import os
import httpx
import json


def test_groq_health_check():
    """Test Groq API directly to diagnose HTTP 404 issue."""
    
    # Current configuration from CloudReasoningPlannerService
    PROVIDER = 'groq'
    BASE_URL = 'https://api.groq.com/openai/v1/chat/completions'
    MODEL = 'llama-3.3-70b-versatile'
    HTTP_METHOD = 'POST'
    
    # Check API key presence
    api_key = os.environ.get('GROQ_API_KEY', '')
    API_KEY_PRESENT = bool(api_key)
    
    print(f"PROVIDER = {PROVIDER}")
    print(f"BASE_URL = {BASE_URL}")
    print(f"ENDPOINT = /chat/completions")
    print(f"MODEL = {MODEL}")
    print(f"HTTP_METHOD = {HTTP_METHOD}")
    print(f"API_KEY_PRESENT = {API_KEY_PRESENT}")
    
    if not API_KEY_PRESENT:
        print("API_KEY_ACCEPTED = N/A (no key)")
        print("HTTP_STATUS = N/A")
        print("REAL_PROVIDER_AVAILABLE = FALSE")
        return
    
    # Try the current model
    messages = [
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Say "test"'},
    ]
    
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                BASE_URL,
                json={'model': MODEL, 'messages': messages, 'temperature': 0.15},
                headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            )
            HTTP_STATUS = resp.status_code
            print(f"HTTP_STATUS = {HTTP_STATUS}")
            
            if resp.status_code == 200:
                print("API_KEY_ACCEPTED = TRUE")
                print("REAL_PROVIDER_AVAILABLE = TRUE")
                print("CONFIGURED_MODEL = VALID")
                data = resp.json()
                print(f"RESPONSE_CLASS = {data.get('object', 'unknown')}")
                print(f"MODEL_USED = {data.get('model', 'unknown')}")
            else:
                print(f"API_KEY_ACCEPTED = UNKNOWN (HTTP {resp.status_code})")
                print("REAL_PROVIDER_AVAILABLE = FALSE")
                print(f"ERROR_BODY = {resp.text[:500]}")
                
                # Try with known valid Groq models to isolate the issue
                alternative_models = [
                    'llama-3.3-70b-versatile',  # Current configured model
                    'llama-3.1-70b-versatile',  # Previously common
                    'mixtral-8x7b-32768',  # Previously common
                    'gemma2-9b-it',  # Previously common
                    'llama-3.3-70b-specdec',  # Speculative decoding
                    'llama-3.2-3b-preview',  # Smaller model
                    'llama-3.2-1b-preview',  # Tiny model
                    'gemma-7b-it',  # Gemma 1
                    'qwen-2.5-7b-instruct',  # Qwen
                    'llama-3.3-8b-instant',  # Newer instant model
                    'llama-3.3-70b-instant',  # Newer instant model
                    'gemma2-9b-it',  # Gemma 2
                    'llama-3.1-8b-instant',  # Llama 3.1 instant
                ]
                
                for alt_model in alternative_models:
                    print(f"\n--- Trying alternative model: {alt_model} ---")
                    resp_alt = client.post(
                        BASE_URL,
                        json={'model': alt_model, 'messages': messages, 'temperature': 0.15},
                        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
                    )
                    print(f"Model {alt_model} HTTP_STATUS = {resp_alt.status_code}")
                    if resp_alt.status_code == 200:
                        print(f"VALID_MODEL_FOUND = {alt_model}")
                        data_alt = resp_alt.json()
                        print(f"RESPONSE_CLASS = {data_alt.get('object', 'unknown')}")
                        print(f"MODEL_USED = {data_alt.get('model', 'unknown')}")
                        break
                    elif resp_alt.status_code == 400:
                        print(f"ERROR_BODY_400 = {resp_alt.text[:500]}")
                    elif resp_alt.status_code == 401:
                        print(f"ERROR_BODY_401 = {resp_alt.text[:200]}")
                
    except Exception as exc:
        print(f"EXCEPTION = {type(exc).__name__}: {str(exc)[:200]}")
        print("HTTP_STATUS = ERROR")
        print("REAL_PROVIDER_AVAILABLE = FALSE")


if __name__ == '__main__':
    test_groq_health_check()
