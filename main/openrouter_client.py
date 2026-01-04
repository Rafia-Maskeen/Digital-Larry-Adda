import requests
from django.conf import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def ask_openrouter(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Digital Larry Adda",
    }

    payload = {
        "model": "mistralai/mistral-7b-instruct",
        "messages": [
            {"role": "system", "content": "You are a transport assistant for Digital Larry Adda."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512,  # 🔥 FIXED
    }

    res = requests.post(
        OPENROUTER_URL,
        headers=headers,
        json=payload,
        timeout=30
    )

    if res.status_code != 200:
        raise Exception(f"OpenRouter {res.status_code}: {res.text}")

    data = res.json()

    if "choices" not in data or not data["choices"]:
        raise Exception(f"Invalid OpenRouter response: {data}")

    return data["choices"][0]["message"]["content"]
