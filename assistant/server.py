"""Room Memory Assistant server.

Run from the repo root:
    python -m uvicorn assistant.server:app --host 127.0.0.1 --port 8000

Then open http://127.0.0.1:8000 in a browser.
"""

import base64
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")  # must run before importing api clients

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from assistant import fish_tts, glm_client

app = FastAPI(title="Room Memory Assistant")

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.post("/api/point-ask")
async def point_ask(image: UploadFile = File(...), question: str = Form("")):
    """Snap a photo -> GLM vision identifies it -> Fish Audio speaks it."""
    image_bytes = await image.read()
    try:
        text = await glm_client.identify_image(
            image_bytes, mime=image.content_type or "image/jpeg", question=question or None
        )
    except Exception as e:  # surface a readable error to the UI
        return JSONResponse({"error": f"GLM vision failed: {e}"}, status_code=502)

    audio_b64 = None
    tts_error = None
    try:
        audio = await fish_tts.synthesize(text)
        audio_b64 = base64.b64encode(audio).decode("ascii")
    except Exception as e:
        tts_error = f"Fish Audio TTS failed: {e}"

    return {"text": text, "audio_b64": audio_b64, "tts_error": tts_error}


CONVERSE_SYSTEM = (
    "You are a friendly medicine specialist voice assistant. The user talks to you "
    "through a camera app; their spoken words are transcribed for you, and a snapshot "
    "from their camera may accompany each question.\n"
    "Answer in plain spoken-style language (2-4 sentences, no markdown): general "
    "information about medicines - what they are used for, how they are typically "
    "taken, common everyday precautions.\n"
    "Safety rules: identify medicine only from packaging/label text, never guess loose "
    "pills; general information only, never personal dosing advice; for anything "
    "personal, tell the user to check with a doctor or pharmacist."
)

# Single-user rolling conversation history (text-only turns are kept).
_history: list[dict] = []
_MAX_TURNS = 12


@app.post("/api/converse")
async def converse(audio: UploadFile = File(...), image: UploadFile | None = File(None)):
    """Voice turn: audio -> Whisper STT -> GLM chat (with camera frame) -> Fish TTS."""
    from assistant import stt  # deferred: first call loads the Whisper model

    audio_bytes = await audio.read()
    try:
        question = stt.transcribe(audio_bytes)
    except Exception as e:
        return JSONResponse({"error": f"Transcription failed: {e}"}, status_code=502)
    if not question:
        return JSONResponse({"error": "I didn't catch that - please try again."}, status_code=422)

    # Build this turn's user message, attaching the camera frame when provided.
    if image is not None:
        image_bytes = await image.read()
        image_b64 = base64.b64encode(image_bytes).decode("ascii")
        user_content = [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
        ]
    else:
        user_content = question

    messages = (
        [{"role": "system", "content": CONVERSE_SYSTEM}]
        + _history[-_MAX_TURNS * 2 :]
        + [{"role": "user", "content": user_content}]
    )
    try:
        reply = await glm_client.chat(messages, model=glm_client.GLM_VISION_MODEL)
    except Exception as e:
        return JSONResponse({"error": f"GLM chat failed: {e}", "question": question}, status_code=502)
    text = (reply.get("content") or "").strip()

    # Keep history text-only so payloads stay small.
    _history.append({"role": "user", "content": question})
    _history.append({"role": "assistant", "content": text})

    audio_b64 = None
    tts_error = None
    try:
        speech = await fish_tts.synthesize(text)
        audio_b64 = base64.b64encode(speech).decode("ascii")
    except Exception as e:
        tts_error = f"Fish Audio TTS failed: {e}"

    return {"question": question, "text": text, "audio_b64": audio_b64, "tts_error": tts_error}


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
