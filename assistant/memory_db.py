"""SQLite object memory built from REMIND runs."""

import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.getenv("MEMORY_DB", Path(__file__).parent / "memory.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS objects (
    scene       TEXT NOT NULL,
    object_id   INTEGER NOT NULL,
    class_id    INTEGER,
    class_name  TEXT,
    first_frame INTEGER,
    last_frame  INTEGER,
    first_ts    REAL,
    last_ts     REAL,
    n_sightings INTEGER,
    best_frame  INTEGER,
    best_conf   REAL,
    best_bbox   TEXT,
    zone        TEXT,
    thumbnail   TEXT,
    run_dir     TEXT,
    PRIMARY KEY (scene, object_id)
);
CREATE TABLE IF NOT EXISTS med_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name     TEXT NOT NULL,
    taken_at REAL NOT NULL,
    snapshot TEXT
);
CREATE TABLE IF NOT EXISTS sightings (
    scene      TEXT NOT NULL,
    object_id  INTEGER NOT NULL,
    frame_idx  INTEGER NOT NULL,
    timestamp  REAL,
    confidence REAL,
    kind       TEXT,
    bbox       TEXT,
    PRIMARY KEY (scene, object_id, frame_idx)
);
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    for col in ("location TEXT", "snapshot TEXT"):
        try:
            conn.execute(f"ALTER TABLE objects ADD COLUMN {col}")
        except sqlite3.OperationalError:
            pass  # column already exists
    return conn


def upsert_live_sighting(
    *,
    scene: str,
    object_id: int,
    class_id: int,
    class_name: str,
    frame_idx: int,
    timestamp: float,
    confidence: float,
    kind: str,
    bbox: list | None,
    thumbnail: str | None,
    snapshot: str | None,
) -> None:
    """Record one live sighting: insert the object row on first sight, then roll last-seen forward."""
    import json as _json

    bbox_json = _json.dumps(bbox) if bbox is not None else None
    with connect() as conn:
        row = conn.execute(
            "SELECT n_sightings, best_conf FROM objects WHERE scene=? AND object_id=?", (scene, object_id)
        ).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO objects (scene, object_id, class_id, class_name, first_frame, last_frame,"
                " first_ts, last_ts, n_sightings, best_frame, best_conf, best_bbox, zone, thumbnail,"
                " run_dir, location, snapshot) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (scene, object_id, class_id, class_name, frame_idx, frame_idx, timestamp, timestamp,
                 1, frame_idx, confidence, bbox_json, None, thumbnail, "live", None, snapshot),
            )
        else:
            updates = {
                "last_frame": frame_idx,
                "last_ts": timestamp,
                "n_sightings": row["n_sightings"] + 1,
                "snapshot": snapshot,
            }
            if thumbnail:
                updates["thumbnail"] = thumbnail
            if confidence >= (row["best_conf"] or 0.0):
                updates["best_conf"] = confidence
                updates["best_frame"] = frame_idx
                updates["best_bbox"] = bbox_json
            sets = ", ".join(f"{k}=?" for k in updates)
            conn.execute(
                f"UPDATE objects SET {sets} WHERE scene=? AND object_id=?",
                [*updates.values(), scene, object_id],
            )
        conn.execute(
            "INSERT OR REPLACE INTO sightings VALUES (?,?,?,?,?,?,?)",
            (scene, object_id, frame_idx, timestamp, confidence, kind, bbox_json),
        )
        conn.commit()


def log_medication(name: str, snapshot: str | None = None) -> None:
    import time

    with connect() as conn:
        conn.execute("INSERT INTO med_log (name, taken_at, snapshot) VALUES (?,?,?)", (name, time.time(), snapshot))
        conn.commit()


def todays_meds() -> list[dict]:
    """Medication log entries since local midnight, oldest first."""
    from datetime import datetime

    midnight = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    with connect() as conn:
        return [
            dict(r)
            for r in conn.execute(
                "SELECT name, taken_at, snapshot FROM med_log WHERE taken_at >= ? ORDER BY taken_at", (midnight,)
            )
        ]


def set_location(scene: str, class_name: str, location: str) -> None:
    """Set the location phrase on the most recently seen object of a class."""
    with connect() as conn:
        conn.execute(
            "UPDATE objects SET location=? WHERE scene=? AND object_id ="
            " (SELECT object_id FROM objects WHERE scene=? AND lower(class_name)=lower(?)"
            "  ORDER BY last_ts DESC LIMIT 1)",
            (location, scene, scene, class_name),
        )
        conn.commit()


def find_object(query: str, scene: str | None = None, limit: int = 5) -> list[dict]:
    """Search remembered objects by (partial) class name, most recently seen first."""
    q = f"%{query.strip().lower().rstrip('s')}%"  # crude singularization: bottles -> bottle
    sql = "SELECT * FROM objects WHERE lower(class_name) LIKE ?"
    args: list = [q]
    if scene:
        sql += " AND scene = ?"
        args.append(scene)
    sql += " ORDER BY (run_dir='live') DESC, last_ts DESC LIMIT ?"
    args.append(limit)
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]


def list_objects(scene: str | None = None) -> list[dict]:
    sql = "SELECT scene, object_id, class_name, zone, n_sightings, last_frame, last_ts FROM objects"
    args: list = []
    if scene:
        sql += " WHERE scene = ?"
        args.append(scene)
    sql += " ORDER BY class_name, object_id"
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql, args).fetchall()]
