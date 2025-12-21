import requests
from django.conf import settings

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

def ask_openrouter(prompt):
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8000",
        "X-Title": "Digital Larry Adda"
    }

    data = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a transport assistant for Digital Larry Adda."},
            {"role": "user", "content": prompt}
        ]
    }

    res = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=20)
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]
