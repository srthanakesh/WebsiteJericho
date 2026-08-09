# 🕊️ Jericho — AI Companion for Seniors

Jericho is a voice-first camera assistant that helps an older person with three everyday struggles:

- **"Where did I put my…?"** — it watches the room, remembers every object it sees, and answers by voice with the location, the time, and a photo.
- **"What is this medicine?"** — it reads the label aloud, explains what it's for in plain language, and warns if the same medicine was already scanned today.
- **"I can't read this."** — point at a letter, bill, or label and it reads the text aloud, then says in one sentence what the document is about.

The phone is only a camera, microphone, and speaker. Everything heavy — speech recognition, object tracking, memory — runs on a PC at home. Only reasoning (GLM) and the voice (Fish Audio) use cloud APIs.

Built on the [REMIND re-identification tracker](../README.md) for persistent object identity.

---

## Features

| Button | What it does |
|---|---|
| 📸 **SNAP** | Photograph an item → Jericho identifies it and speaks a short description. Medicines are read from the label only. |
| 💬 **ASK** | Type a question about what the camera sees; your question and the answer appear as an on-screen conversation. |
| 🎤 **HOLD** | Hold to talk. Speech is transcribed locally (Whisper), answered by GLM with conversation memory, and spoken back in the Sarah voice. |
| 👁 **WATCH** | Live room memory. Every 8 seconds a frame goes through REMIND (persistent object IDs) and GLM names natural locations ("on the kitchen counter"). Then ask: *"where is my teddy bear?"* |
| 📖 **READ** | Reads small print aloud — letters, bills, expiry dates — keeping numbers and dates exact, with a one-sentence summary. |

**Medication Guardian:** every medicine scan is logged. Scanning the same medicine twice in a day triggers a spoken warning *before* anything else: "you already scanned this at 8:00 AM — do not take it again." Ask *"what have I taken today?"* any time.

---

## Architecture

```
PHONE (browser) ── HTTPS ──> FastAPI server (PC)
  camera + mic + speaker        │
                                ├── Whisper STT        (local)
                                ├── REMIND tracker     (local)  YOLO + DINOv3 re-ID
                                ├── GLM-4.6V           (cloud)  vision + chat + tools
                                ├── Fish Audio TTS     (cloud)  "Sarah" voice
                                └── SQLite memory.db   (local)  objects · sightings · med_log
```

The voice agent has two tools it calls on its own: `find_object(query)` (object memory search → location + time + photo) and `med_history()` (today's medication log).

**Why REMIND?** A caption-only approach logs "a bottle" fresh every time and confuses duplicates. REMIND keeps persistent identities — six bottles stay six distinct objects across occlusions and reappearances — while GLM adds the human-friendly *where*.

---

## Setup

### 1. Install dependencies

```bash
pip install torch torchvision transformers scikit-learn scipy numpy opencv-python tqdm psutil ultralytics
pip install -r assistant/requirements.txt
```

YOLO segmentation weights go in `yolo/` (e.g. `yolov8n-seg.pt`). DINOv3 downloads automatically on first run.

### 2. API keys

```bash
cp assistant/.env.example assistant/.env
```

Fill in:
- `GLM_API_KEY` — from [z.ai](https://z.ai) (models `glm-4.6v` / `glm-4.6`) or bigmodel.cn (adjust `GLM_BASE_URL` and model names per the comments)
- `FISH_API_KEY` + `FISH_VOICE_ID` — from [fish.audio](https://fish.audio); the voice ID comes from your chosen voice model's page

`.env` is git-ignored — keys never leave your machine.

### 3. HTTPS certificate (needed for phone camera access)

Browsers only allow camera/mic over HTTPS. Generate a self-signed cert for your PC's LAN IP:

```bash
mkdir -p assistant/certs
openssl req -x509 -newkey rsa:2048 -keyout assistant/certs/key.pem \
  -out assistant/certs/cert.pem -days 825 -nodes \
  -subj "//CN=<YOUR-PC-LAN-IP>" \
  -addext "subjectAltName=IP:<YOUR-PC-LAN-IP>,IP:127.0.0.1,DNS:localhost"
```

Allow the port through Windows Firewall (admin):

```
netsh advfirewall firewall add rule name="Jericho 8443" dir=in action=allow protocol=TCP localport=8443
```

### 4. Run

```bash
python -m uvicorn assistant.server:app --host 0.0.0.0 --port 8443 \
  --ssl-keyfile assistant/certs/key.pem --ssl-certfile assistant/certs/cert.pem
```

- **Phone** (same Wi-Fi): open `https://<YOUR-PC-LAN-IP>:8443`, accept the certificate warning once, allow camera + mic.
- **PC**: `https://localhost:8443`.

---

## Room walkthrough memory (optional, offline)

Besides live WATCH mode, you can ingest a recorded walkthrough:

```bash
# 1. Track a video with REMIND (video in testData/videos/<scene>/video.mp4)
python main.py <scene> yolov8n-seg.pt --input-video-fps 10 --save-output-video

# 2. Ingest the run into the object memory (with thumbnails)
python -m assistant.ingest outputs/video_runs/<scene>_<timestamp>
```

Label room zones per frame range in `assistant/zones.yaml`:

```yaml
my_room:
  - frames: [0, 150]
    zone: "kitchen"
  - frames: [151, 400]
    zone: "bedroom shelf"
```

Live WATCH memory resets each server restart (tracker IDs restart); ingested walkthrough scenes persist.

---

## Safety notes

Jericho is a reading aid, not a medical authority:

- Medicine identity comes **only from packaging/label text** — it refuses to guess loose pills.
- It gives general information, never personal dosing advice, and always defers to a pharmacist or doctor.
- Treat every medicine answer as something to confirm on the label or with a professional.

---

## File map

```
assistant/
  server.py          FastAPI: endpoints, tool-calling loop, persona, med guardian
  static/index.html  the whole UI — camera, buttons, chat overlay, watch loop
  glm_client.py      GLM calls: identify (persona) / vision (bare) / chat (tools)
  fish_tts.py        Fish Audio TTS client
  stt.py             faster-whisper local transcription
  live_tracker.py    live REMIND session (lazy init, busy-frame dropping, DB upserts)
  memory_db.py       SQLite schema, find_object, med_log, locations
  ingest.py          offline REMIND run -> database + thumbnails
  zones.yaml         frame-range -> zone labels for walkthrough scenes
```
