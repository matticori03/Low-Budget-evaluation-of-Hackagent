import json
import urllib.request
import urllib.error

url = "http://localhost:8000/v1/chat/completions"
data = {
    "model": "vulnerable-bank-local",
    "messages": [
        {"role": "user", "content": "Hello, how are you?"}
    ]
}

req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode())
        print("Success:", json.dumps(result, indent=2))
except urllib.error.URLError as e:
    print("Error:", e)
