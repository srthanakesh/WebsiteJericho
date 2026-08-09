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


def _apply_med_guardian(text: str) -> str:
    """Parse the MED_JSON marker line; warn if this medicine was already taken today."""
    from datetime import datetime

    from assistant import memory_db

    marker = "MED_JSON:"
    idx = text.find(marker)
    if idx == -1:
        return text
    payload = text[idx + len(marker) :].strip()
    text = text[:idx].strip()
    try:
        name = (json.loads(payload).get("name") or "").strip()
    except Exception:
        return text
    if not name:
        return text

    already = [m for m in memory_db.todays_meds() if m["name"].lower() == name.lower()]
    if already:
        first_time = datetime.fromtimestamp(already[0]["taken_at"]).strftime("%I:%M %p").lstrip("0")
        warning = (
            f"Careful - you already scanned {name} today at {first_time}. "
            "If you already took it, please do not take it again. "
        )
        text = warning + text
    memory_db.log_medication(name)
    return text


@app.post("/api/point-ask")
async def point_ask(image: UploadFile = File(...), question: str = Form(""), mode: str = Form("")):
    """Snap a photo -> GLM vision identifies (or reads) it -> Fish Audio speaks it."""
    image_bytes = await image.read()
    mime = image.content_type or "image/jpeg"
    try:
        if mode == "read":
            text = await glm_client.vision(image_bytes, glm_client.READ_WORLD_PROMPT, mime=mime)
        else:
            text = await glm_client.identify_image(image_bytes, mime=mime, question=question or None)
    except Exception as e:  # surface a readable error to the UI
        return JSONResponse({"error": f"GLM vision failed: {e}"}, status_code=502)
    if mode != "read":
        text = _apply_med_guardian(text)

    audio_b64 = None
    tts_error = None
    try:
        audio = await fish_tts.synthesize(text)
        audio_b64 = base64.b64encode(audio).decode("ascii")
    except Exception as e:
        tts_error = f"Fish Audio TTS failed: {e}"

    return {"text": text, "audio_b64": audio_b64, "tts_error": tts_error}


CONVERSE_SYSTEM = (
    "You are Jericho, a warm and patient voice companion helping an older person with "
    "everyday life: finding their things, understanding their medicines, and reading the "
    "world around them. They talk to you through a camera app; their spoken words are "
    "transcribed for you, and a snapshot from their camera may accompany each question.\n"
    "Speak gently and clearly in short simple sentences (2-4 of them, no markdown), one "
    "idea at a time. Be reassuring, never rushed or condescending. For medicines give "
    "general information: what they are used for, how they are typically taken, common "
    "everyday precautions.\n"
    "Safety rules: identify medicine only from packaging/label text, never guess loose "
    "pills; general information only, never personal dosing advice; for anything "
    "personal, tell the user to check with a doctor or pharmacist.\n"
    "Finding items: when the user asks where an item is (keys, bottle, book, medicine, "
    "etc.), call the find_object tool with a short item name. Answer from its results: "
    "prefer the location phrase and seen_at time when available ('your keys were on the "
    "kitchen counter around 10:15 AM'); otherwise say the zone and last seen frame. If "
    "there are several matches mention how many and describe the most recent. If nothing "
    "is found, say you have not seen it yet.\n"
    "Medicines taken today: when asked what medicines they took or whether they already "
    "took something, call the med_history tool and answer from it with the times."
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


MED_HISTORY_TOOL = {
    "type": "function",
    "function": {
        "name": "med_history",
        "description": "Get the list of medicines the user has scanned/taken today, with times.",
        "parameters": {"type": "object", "properties": {}},
    },
}


def _run_med_history() -> str:
    from datetime import datetime

    from assistant import memory_db

    meds = [
        {"name": m["name"], "time": datetime.fromtimestamp(m["taken_at"]).strftime("%I:%M %p").lstrip("0")}
        for m in memory_db.todays_meds()
    ]
    return json.dumps({"today": meds})


def _run_find_object(query: str) -> tuple[str, list[dict]]:
    """Execute the tool; return (JSON for the model, match list for the UI)."""
    from datetime import datetime

    from assistant import memory_db

    rows = memory_db.find_object(query)
    matches = []
    for r in rows:
        d = dict(r)
        is_live = d.get("run_dir") == "live"
        seen_at = (
            datetime.fromtimestamp(d["last_ts"]).strftime("%I:%M %p").lstrip("0")
            if is_live and d.get("last_ts")
            else None
        )
        matches.append(
            {
                "object_id": d["object_id"],
                "class_name": d["class_name"],
                "scene": d["scene"],
                "zone": d["zone"],
                "location": d.get("location"),
                "seen_at": seen_at,
                "last_frame": d["last_frame"],
                "n_sightings": d["n_sightings"],
                "thumbnail": f"/thumbnails/{Path(d['thumbnail']).name}" if d.get("thumbnail") else None,
                "snapshot": f"/snapshots/{d['snapshot']}" if d.get("snapshot") else None,
            }
        )
    model_view = [
        {k: m[k] for k in ("class_name", "zone", "location", "seen_at", "last_frame", "n_sightings")}
        for m in matches
    ]
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
    tools = [FIND_OBJECT_TOOL, MED_HISTORY_TOOL]
    try:
        reply = await glm_client.chat(messages, tools=tools, model=glm_client.GLM_VISION_MODEL)
        for _ in range(3):  # resolve tool calls, at most a few rounds
            tool_calls = reply.get("tool_calls")
            if not tool_calls:
                break
            messages.append(reply)
            for call in tool_calls:
                fn_name = call["function"].get("name")
                args = json.loads(call["function"].get("arguments") or "{}")
                if fn_name == "med_history":
                    result_json = _run_med_history()
                else:
                    result_json, matches = _run_find_object(args.get("query", ""))
                    ui_matches.extend(matches)
                messages.append({"role": "tool", "content": result_json, "tool_call_id": call.get("id")})
            reply = await glm_client.chat(messages, tools=tools, model=glm_client.GLM_VISION_MODEL)
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


LOCATION_PROMPT = (
    "You are helping a room-memory system. Look at this photo and, for each item class "
    "listed below, describe WHERE that item is in one short natural phrase a person would "
    "say (e.g. 'on the kitchen counter', 'on the shelf by the window', 'on the bed').\n"
    "Items: {items}\n"
    "Reply with ONLY a JSON object mapping each item name to its location phrase, no other text."
)


@app.post("/api/monitor-frame")
async def monitor_frame(image: UploadFile = File(...)):
    """Live monitoring: one camera frame -> REMIND tracking + GLM location naming."""
    import asyncio

    import cv2
    import numpy as np

    from assistant import memory_db
    from assistant.live_tracker import tracker

    data = await image.read()
    frame = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        return JSONResponse({"error": "Bad image"}, status_code=400)

    result = await asyncio.to_thread(tracker.process, frame)
    if result is None:
        return {"skipped": True}

    # Name locations of what we saw (one GLM call per processed frame).
    classes = sorted({o["class_name"] for o in result["objects"]})
    if classes:
        try:
            raw = await glm_client.vision(data, LOCATION_PROMPT.format(items=", ".join(classes)))
            start, end = raw.find("{"), raw.rfind("}")
            if start != -1 and end > start:
                locations = json.loads(raw[start : end + 1])
                for cls, loc in locations.items():
                    if isinstance(loc, str) and loc.strip():
                        memory_db.set_location("live", cls, loc.strip())
        except Exception:
            pass  # location naming is best-effort; tracking already saved

    return {"skipped": False, "objects": result["objects"], "frame_idx": result["frame_idx"]}


THUMB_DIR = Path(__file__).parent / "thumbnails"
THUMB_DIR.mkdir(exist_ok=True)
SNAP_DIR = Path(__file__).parent / "snapshots"
SNAP_DIR.mkdir(exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=THUMB_DIR), name="thumbnails")
app.mount("/snapshots", StaticFiles(directory=SNAP_DIR), name="snapshots")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
