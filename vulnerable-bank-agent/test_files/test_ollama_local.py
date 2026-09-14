import urllib.request
import json

try:
    url = "http://localhost:11434/api/tags"
    with urllib.request.urlopen(url, timeout=5) as response:
        print("Ollama API is responding.")
except Exception as e:
    print(f"Error connecting to Ollama: {e}")
