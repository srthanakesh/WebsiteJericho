"""Live REMIND tracking on frames streamed from the camera UI."""

import threading
import time
from pathlib import Path

import cv2

from assistant import memory_db
from config.config_loader import Config
from pipeline.initialization import initialize_system
from pipeline.reid_pipeline import ReIDPipeline
from scripts.run_video_tracking import _entries_by_det_id

REPO_ROOT = Path(__file__).resolve().parents[1]
SNAP_DIR = Path(__file__).parent / "snapshots"
THUMB_DIR = Path(__file__).parent / "thumbnails"

LIVE_SCENE = "live"


class LiveTracker:
    """Lazy singleton around REMIND's ReIDPipeline for one live session."""

    def __init__(self):
        self._lock = threading.Lock()
        self._pipeline = None
        self._frame_idx = 0

    def _ensure_pipeline(self) -> ReIDPipeline:
        if self._pipeline is None:
            # New live session: object ids restart from 0, so drop stale live rows.
            with memory_db.connect() as conn:
                conn.execute("DELETE FROM objects WHERE scene = ?", (LIVE_SCENE,))
                conn.execute("DELETE FROM sightings WHERE scene = ?", (LIVE_SCENE,))
                conn.commit()
            cfg = Config(str(REPO_ROOT / "config" / "default_config.yaml")).to_dict()
            cfg.setdefault("paths", {})["output_dir"] = str(SNAP_DIR / "run")
            cfg.setdefault("detector", {})["backend"] = "yolo"
            yolo_cfg = cfg.setdefault("yolo", {})
            yolo_cfg["model_label"] = "CUSTOM"
            yolo_cfg["models"] = {"CUSTOM": str(REPO_ROOT / "yolo" / "yolov8n-seg.pt")}
            yolo_cfg["conf_th"] = 0.25
            yolo_cfg["iou_th"] = 0.7
            yolo_cfg["max_det"] = 100
            cfg.setdefault("system", {})["input_width_size"] = 960
            cfg.setdefault("runtime", {})["device"] = "auto"
            cfg.setdefault("timing", {})["enabled"] = False
            cfg.setdefault("timing", {})["table"] = False
            ctx = initialize_system(cfg)
            self._pipeline = ReIDPipeline(ctx)
        return self._pipeline

    def process(self, frame_bgr) -> dict | None:
        """Run one frame through REMIND and update the live-scene memory.

        Returns a summary dict, or None if a frame is already being processed
        (callers should treat that as "skipped").
        """
        if not self._lock.acquire(blocking=False):
            return None
        try:
            pipeline = self._ensure_pipeline()
            now = time.time()
            frame_idx = self._frame_idx
            self._frame_idx += 1

            p_out, _a_out, u_out = pipeline.process_frame(frame_bgr, frame_id=frame_idx, timestamp=now)

            aligned = (p_out.debug or {}).get("frame_aligned_bgr")
            if aligned is None:
                aligned = frame_bgr

            SNAP_DIR.mkdir(exist_ok=True)
            THUMB_DIR.mkdir(exist_ok=True)
            snapshot_name = f"live_{frame_idx:06d}.jpg"
            cv2.imwrite(str(SNAP_DIR / snapshot_name), aligned)

            entries = _entries_by_det_id(u_out)
            seen = []
            for det in p_out.detections:
                entry = entries.get(int(det.detection_id))
                if not entry or entry.get("object_id") is None:
                    continue
                object_id = int(entry["object_id"])
                class_name = getattr(det, "class_name", None) or f"class_{det.class_id}"

                thumb_path = None
                if det.bbox is not None:
                    x1, y1, x2, y2 = (int(v) for v in det.bbox)
                    h, w = aligned.shape[:2]
                    pad = 10
                    crop = aligned[max(0, y1 - pad) : min(h, y2 + pad), max(0, x1 - pad) : min(w, x2 + pad)]
                    if crop.size:
                        thumb_path = str(THUMB_DIR / f"{LIVE_SCENE}_obj{object_id}.jpg")
                        cv2.imwrite(thumb_path, crop)

                memory_db.upsert_live_sighting(
                    scene=LIVE_SCENE,
                    object_id=object_id,
                    class_id=int(det.class_id),
                    class_name=class_name,
                    frame_idx=frame_idx,
                    timestamp=now,
                    confidence=float(det.confidence or 0.0),
                    kind=entry["kind"],
                    bbox=[float(v) for v in det.bbox] if det.bbox is not None else None,
                    thumbnail=thumb_path,
                    snapshot=snapshot_name,
                )
                seen.append({"object_id": object_id, "class_name": class_name})

            return {
                "frame_idx": frame_idx,
                "objects": seen,
                "snapshot": snapshot_name,
                "summary": getattr(u_out, "summary", None),
            }
        finally:
            self._lock.release()


tracker = LiveTracker()
