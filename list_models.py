import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

print("Fetching models from OpenRouter...")
headers = {}
if api_key:
    headers["Authorization"] = f"Bearer {api_key}"
response = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
if response.status_code == 200:
    models = response.json().get("data", [])
    print(f"Supported models on OpenRouter ({len(models)}):")
    for m in models:
        if "gpt-oss" in m.get("id", "").lower() or "free" in m.get("id", "").lower():
            print(f"- {m.get('id')}")
else:
    print(f"Failed to fetch models: {response.text}")
