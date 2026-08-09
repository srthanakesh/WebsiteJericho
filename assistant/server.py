"""Room Memory Assistant server.

Run from the repo root:
    python -m uvicorn assistant.server:app --host 127.0.0.1 --port 8000

Then open http://127.0.0.1:8000 in a browser.
"""

import base64
import json
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
    "You are a friendly medicine specialist and room-memory voice assistant. The user "
    "talks to you through a camera app; their spoken words are transcribed for you, and "
    "a snapshot from their camera may accompany each question.\n"
    "Answer in plain spoken-style language (2-4 sentences, no markdown): general "
    "information about medicines - what they are used for, how they are typically "
    "taken, common everyday precautions.\n"
    "Safety rules: identify medicine only from packaging/label text, never guess loose "
    "pills; general information only, never personal dosing advice; for anything "
    "personal, tell the user to check with a doctor or pharmacist.\n"
    "Finding items: when the user asks where an item is (keys, bottle, book, medicine, "
    "etc.), call the find_object tool with a short item name. Answer from its results: "
    "say the zone it was last seen in, roughly when in the walkthrough (last seen frame "
    "number), and if there are several matches mention how many and describe the most "
    "recent. If nothing is found, say you have not seen it in the scanned room yet."
)

FIND_OBJECT_TOOL = {
    "type": "function",
    "function": {
        "name": "find_object",
        "description": (
            "Search the scanned room memory (built from a camera walkthrough) for an "
            "item and return where it was last seen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Short item name to search for, e.g. 'bottle', 'keys', 'laptop'",
                }
            },
            "required": ["query"],
        },
    },
}


def _run_find_object(query: str) -> tuple[str, list[dict]]:
    """Execute the tool; return (JSON for the model, match list for the UI)."""
    from assistant import memory_db

    rows = memory_db.find_object(query)
    matches = [
        {
            "object_id": r["object_id"],
            "class_name": r["class_name"],
            "scene": r["scene"],
            "zone": r["zone"],
            "last_frame": r["last_frame"],
            "last_ts": r["last_ts"],
            "n_sightings": r["n_sightings"],
            "thumbnail": f"/thumbnails/{Path(r['thumbnail']).name}" if r["thumbnail"] else None,
        }
        for r in rows
    ]
    model_view = [{k: m[k] for k in ("class_name", "zone", "last_frame", "last_ts", "n_sightings")} for m in matches]
    return json.dumps({"matches": model_view}), matches

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
    ui_matches: list[dict] = []
    try:
        reply = await glm_client.chat(messages, tools=[FIND_OBJECT_TOOL], model=glm_client.GLM_VISION_MODEL)
        for _ in range(3):  # resolve tool calls, at most a few rounds
            tool_calls = reply.get("tool_calls")
            if not tool_calls:
                break
            messages.append(reply)
            for call in tool_calls:
                args = json.loads(call["function"].get("arguments") or "{}")
                result_json, matches = _run_find_object(args.get("query", ""))
                ui_matches.extend(matches)
                messages.append({"role": "tool", "content": result_json, "tool_call_id": call.get("id")})
            reply = await glm_client.chat(messages, tools=[FIND_OBJECT_TOOL], model=glm_client.GLM_VISION_MODEL)
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

    return {
        "question": question,
        "text": text,
        "audio_b64": audio_b64,
        "tts_error": tts_error,
        "matches": ui_matches or None,
    }


THUMB_DIR = Path(__file__).parent / "thumbnails"
THUMB_DIR.mkdir(exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=THUMB_DIR), name="thumbnails")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
