import json
import urllib.request
import urllib.error

url = "http://localhost:11434/api/generate"
data = {
    "model": "llama3.1:8b",
    "prompt": "Hello",
    "stream": False
}

req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'}
)

try:
    with urllib.request.urlopen(req, timeout=10) as response:
        print("Success: Ollama is reachable")
except urllib.error.URLError as e:
    print("Error:", e)
except Exception as e:
    print("Timeout or other error:", e)
