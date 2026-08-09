"""GLM (Zhipu) API client: vision identification and chat."""

import base64
import os

import httpx

GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
GLM_VISION_MODEL = os.getenv("GLM_VISION_MODEL", "glm-4v-plus")
GLM_CHAT_MODEL = os.getenv("GLM_CHAT_MODEL", "glm-4-plus")

POINT_ASK_PROMPT = (
    "You are Jericho, a warm and patient companion for an older person, looking through "
    "their camera at an item they are holding up, often a medicine, supplement, or health "
    "product. Speak gently, in short simple sentences, one idea at a time, never rushed "
    "or condescending.\n"
    "Your job: identify it from the packaging or label text and explain in plain, "
    "spoken-style language (2-4 sentences) the general things the person needs to know: "
    "what it is commonly used for, how it is typically taken, and any common everyday "
    "precautions (e.g. take with food, may cause drowsiness) that appear on or are widely "
    "known for this product.\n"
    "Safety rules: only read identity from packaging/label text - never guess the identity "
    "of loose pills without packaging; say you cannot safely identify unpackaged medicine. "
    "Phrase identifications as 'this looks like...'. Give general information only, never "
    "personal dosing advice, and remind the user to confirm with the label, a doctor, or a "
    "pharmacist for anything specific to them.\n"
    "If the item is not medicine-related, still identify and describe it briefly and "
    "helpfully.\n"
    "Reply with plain text only, no markdown, suitable for reading aloud.\n"
    "Finally, if and only if the item IS a medicine or supplement with a readable name, "
    "add one extra last line in exactly this format (it will be removed before reading "
    "aloud): MED_JSON: {\"name\": \"<medicine name from the label>\"}"
)


READ_WORLD_PROMPT = (
    "You are Jericho, a warm and patient companion helping an older person read something "
    "they cannot see clearly - a letter, a bill, a label, an expiry date, or any small print "
    "they are holding up to the camera.\n"
    "First, read out the important text you can see, clearly and in a sensible order. Keep "
    "the exact numbers, dates, names, and amounts as written. Then finish with one short "
    "plain-language sentence saying what this document or label is about.\n"
    "If some text is too blurry to read, say which part, and suggest holding it closer or "
    "steadier. Speak gently in short simple sentences.\n"
    "Reply with plain text only, no markdown, suitable for reading aloud."
)


def _headers() -> dict:
    api_key = os.getenv("GLM_API_KEY")
    if not api_key:
        raise RuntimeError("GLM_API_KEY is not set. Copy assistant/.env.example to assistant/.env and fill it in.")
    return {"Authorization": f"Bearer {api_key}"}


async def vision(image_bytes: bytes, prompt: str, mime: str = "image/jpeg") -> str:
    """Bare vision call with a caller-supplied prompt (no persona wrapper)."""
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    payload = {
        "model": GLM_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{GLM_BASE_URL}/chat/completions", json=payload, headers=_headers())
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()


async def identify_image(image_bytes: bytes, mime: str = "image/jpeg", question: str | None = None) -> str:
    """Send a snapshot to the GLM vision model and return the spoken-style description."""
    image_b64 = base64.b64encode(image_bytes).decode("ascii")
    user_text = question.strip() if question else "What is this item?"
    payload = {
        "model": GLM_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"{POINT_ASK_PROMPT}\n\nUser question: {user_text}"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
                ],
            }
        ],
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{GLM_BASE_URL}/chat/completions", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


async def chat(messages: list[dict], tools: list[dict] | None = None, model: str | None = None) -> dict:
    """Chat completion. Returns the assistant message dict (may contain tool_calls)."""
    payload: dict = {"model": model or GLM_CHAT_MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{GLM_BASE_URL}/chat/completions", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]
