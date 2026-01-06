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
        "model": "openai/gpt-4o-mini",
        "messages": [
            {
  "role": "system",
  "content": (
    "You are Digital Larry Adda's transport assistant.\n"
    "RULES:\n"
    "- ONLY answer transport-related questions (routes, buses, fares, schedules).\n"
    "- If exact data is not available, clearly say you do not have the information.\n"
    "- NEVER guess fares, times, or routes.\n"
    "- NEVER invent prices or locations.\n"
    "- Keep answers short, clear, and factual.\n"
    "- Do NOT include system tokens, markdown, [INST], <s>, or explanations.\n"
    "- Respond in plain text only."
  )
},

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

    content = data["choices"][0]["message"]["content"]

# 🔥 Clean junk tokens from Mistral-style models
    content = content.replace("[INST]", "").replace("</s>", "").replace("<s>", "").strip()

    return content
