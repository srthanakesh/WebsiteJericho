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
    return conn


def find_object(query: str, scene: str | None = None, limit: int = 5) -> list[dict]:
    """Search remembered objects by (partial) class name, most recently seen first."""
    q = f"%{query.strip().lower().rstrip('s')}%"  # crude singularization: bottles -> bottle
    sql = "SELECT * FROM objects WHERE lower(class_name) LIKE ?"
    args: list = [q]
    if scene:
        sql += " AND scene = ?"
        args.append(scene)
    sql += " ORDER BY last_frame DESC LIMIT ?"
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
