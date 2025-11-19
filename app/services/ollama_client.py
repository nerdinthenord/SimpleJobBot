import os
import httpx

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://simplejobbot-ollama:11434")
MODEL = os.getenv("JOBBOT_MODEL", "llama3")


async def ollama_chat(prompt: str) -> str:
    """
    Call Ollama /api/generate with a plain prompt and return the text response.
    """
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
    }

    # Give the model more time to respond – 10 minutes total
    timeout = httpx.Timeout(600.0, connect=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(f"{OLLAMA_HOST}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        message = data.get("response")
        if not message:
            raise RuntimeError("Ollama response missing 'response' field")
        return message
