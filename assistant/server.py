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


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
