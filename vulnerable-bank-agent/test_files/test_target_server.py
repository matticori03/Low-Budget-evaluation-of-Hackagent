import urllib.request
import json
import time

print("Testing Target Agent Server...")
try:
    url = "http://localhost:8000/v1/chat/completions"
    data = {
        "model": "vulnerable-bank-local",
        "messages": [
            {"role": "user", "content": "Hello, this is a test."}
        ]
    }
    
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    start = time.time()
    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode())
        end = time.time()
        print(f"Success! Response took {end-start:.2f}s")
        print("Response Snippet:", json.dumps(result, indent=2)[:500])
except Exception as e:
    print(f"Error connecting to target server: {e}")
