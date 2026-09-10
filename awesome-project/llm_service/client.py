import requests
from config import LLM_URL

def call_llm(prompt: str, timeout: int = 15) -> str:
    r = requests.post(LLM_URL, json={"text": prompt}, timeout=timeout)
    data = r.json()
    return data.get("response") or data.get("text") or data.get("message") or str(data)
