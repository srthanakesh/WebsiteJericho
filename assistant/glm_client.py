"""GLM (Zhipu) API client: vision identification and chat."""

import base64
import os

import httpx

GLM_BASE_URL = os.getenv("GLM_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
GLM_VISION_MODEL = os.getenv("GLM_VISION_MODEL", "glm-4v-plus")
GLM_CHAT_MODEL = os.getenv("GLM_CHAT_MODEL", "glm-4-plus")

POINT_ASK_PROMPT = (
    "You are a helpful assistant looking at a photo the user just took of an item "
    "they are holding up to the camera. Identify the item and give a short spoken-style "
    "description (2-4 sentences).\n"
    "If it is a medicine or supplement: read the name and details from the packaging or "
    "label text only, and give a one-sentence plain-language note on what it is commonly "
    "used for. Never guess the identity of loose pills without packaging - instead say "
    "you cannot safely identify unpackaged medicine. Phrase identifications as 'this "
    "looks like...' and remind the user to confirm on the label or with a pharmacist "
    "before taking anything.\n"
    "Reply with plain text only, no markdown, suitable for reading aloud."
)


def _headers() -> dict:
    api_key = os.getenv("GLM_API_KEY")
    if not api_key:
        raise RuntimeError("GLM_API_KEY is not set. Copy assistant/.env.example to assistant/.env and fill it in.")
    return {"Authorization": f"Bearer {api_key}"}


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


async def chat(messages: list[dict], tools: list[dict] | None = None) -> dict:
    """Plain chat completion. Returns the assistant message dict (may contain tool_calls)."""
    payload: dict = {"model": GLM_CHAT_MODEL, "messages": messages}
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{GLM_BASE_URL}/chat/completions", json=payload, headers=_headers())
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]
