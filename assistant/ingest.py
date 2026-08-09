"""Ingest a REMIND run folder into the SQLite object memory.

Usage (from repo root):
    python -m assistant.ingest outputs/video_runs/my_room_20260808_182340
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import cv2
import yaml

from assistant import memory_db

THUMB_DIR = Path(__file__).parent / "thumbnails"
ZONES_PATH = Path(__file__).parent / "zones.yaml"


def load_zones(scene: str) -> list[dict]:
    if not ZONES_PATH.exists():
        return []
    zones = yaml.safe_load(ZONES_PATH.read_text()) or {}
    return zones.get(scene, [])


def zone_for_frame(zones: list[dict], frame_idx: int) -> str | None:
    for z in zones:
        lo, hi = z["frames"]
        if lo <= frame_idx <= hi:
            return z["zone"]
    return None


def ingest(run_dir: Path) -> None:
    summary = json.loads((run_dir / "summary.json").read_text())
    scene = summary["scene"]
    source = summary["source"]
    zones = load_zones(scene)

    # Collect sightings per confirmed object (skip ambiguous/provisional: object_id null).
    sightings = defaultdict(list)
    with open(run_dir / "detections.jsonl") as f:
        for line in f:
            frame = json.loads(line)
            for det in frame["detections"]:
                if det.get("object_id") is None:
                    continue
                sightings[det["object_id"]].append(
                    {
                        "frame_idx": frame["frame_idx"],
                        "timestamp": frame["timestamp"],
                        "confidence": det.get("confidence") or 0.0,
                        "kind": det["kind"],
                        "bbox": det["bbox_xyxy"],
                        "class_id": det.get("class_id"),
                        "class_name": det.get("class_name"),
                    }
                )

    THUMB_DIR.mkdir(exist_ok=True)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise SystemExit(f"Cannot open source video for thumbnails: {source}")

    with memory_db.connect() as conn:
        conn.execute("DELETE FROM objects WHERE scene = ?", (scene,))
        conn.execute("DELETE FROM sightings WHERE scene = ?", (scene,))

        for object_id, sights in sorted(sightings.items()):
            sights.sort(key=lambda s: s["frame_idx"])
            best = max(sights, key=lambda s: s["confidence"])
            last = sights[-1]

            # Thumbnail: crop best sighting's bbox from the source video frame.
            thumb_path = None
            cap.set(cv2.CAP_PROP_POS_MSEC, best["timestamp"] * 1000.0)
            ok, frame_img = cap.read()
            if ok:
                x1, y1, x2, y2 = (int(v) for v in best["bbox"])
                h, w = frame_img.shape[:2]
                pad = 10
                crop = frame_img[max(0, y1 - pad) : min(h, y2 + pad), max(0, x1 - pad) : min(w, x2 + pad)]
                if crop.size:
                    thumb_path = str(THUMB_DIR / f"{scene}_obj{object_id}.jpg")
                    cv2.imwrite(thumb_path, crop)

            conn.execute(
                "INSERT INTO objects VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    scene,
                    object_id,
                    best["class_id"],
                    best["class_name"],
                    sights[0]["frame_idx"],
                    last["frame_idx"],
                    sights[0]["timestamp"],
                    last["timestamp"],
                    len(sights),
                    best["frame_idx"],
                    best["confidence"],
                    json.dumps(best["bbox"]),
                    zone_for_frame(zones, last["frame_idx"]),
                    thumb_path,
                    str(run_dir),
                ),
            )
            conn.executemany(
                "INSERT OR REPLACE INTO sightings VALUES (?,?,?,?,?,?,?)",
                [
                    (scene, object_id, s["frame_idx"], s["timestamp"], s["confidence"], s["kind"], json.dumps(s["bbox"]))
                    for s in sights
                ],
            )
        conn.commit()
    cap.release()

    objs = memory_db.list_objects(scene)
    print(f"Ingested scene '{scene}': {len(objs)} objects from {run_dir}")
    for o in objs:
        print(
            f"  #{o['object_id']:<3} {o['class_name']:<14} zone={o['zone'] or '?':<12} "
            f"sightings={o['n_sightings']:<3} last_frame={o['last_frame']}"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path, help="REMIND run folder (contains summary.json)")
    args = parser.parse_args()
    ingest(args.run_dir)
