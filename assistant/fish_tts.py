"""Fish Audio TTS client (Sarah voice via reference_id)."""

import os

import httpx

FISH_TTS_URL = "https://api.fish.audio/v1/tts"


async def synthesize(text: str) -> bytes:
    """Convert text to speech with the configured Fish Audio voice. Returns MP3 bytes."""
    api_key = os.getenv("FISH_API_KEY")
    if not api_key:
        raise RuntimeError("FISH_API_KEY is not set. Copy assistant/.env.example to assistant/.env and fill it in.")
    voice_id = os.getenv("FISH_VOICE_ID")
    if not voice_id:
        raise RuntimeError("FISH_VOICE_ID is not set (the Sarah voice reference id from fish.audio).")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": os.getenv("FISH_TTS_MODEL", "speech-1.5"),
    }
    payload = {
        "text": text,
        "reference_id": voice_id,
        "format": "mp3",
        "latency": "normal",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(FISH_TTS_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.content
