"""SQLite persistence for one wardrobe with physically positioned compartments."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("DATABASE_PATH", ROOT / "data" / "wardrobe.sqlite3"))
UPLOADS_PATH = Path(os.environ.get("UPLOADS_PATH", ROOT / "uploads"))

CATEGORIES = ["shirt", "pants", "dress", "jacket", "skirt", "accessory", "other"]
COMPARTMENT_KINDS = ["hanger", "shelf", "drawer"]


def connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def db():
    conn = connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    UPLOADS_PATH.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS wardrobes (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          code TEXT NOT NULL DEFAULT 'W01',
          name TEXT NOT NULL,
          location TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS compartments (
          id INTEGER PRIMARY KEY,
          wardrobe_id INTEGER NOT NULL REFERENCES wardrobes(id),
          code TEXT NOT NULL UNIQUE,
          label TEXT NOT NULL,
          kind TEXT NOT NULL CHECK (kind IN ('hanger','shelf','drawer')),
          row_position INTEGER NOT NULL CHECK (row_position BETWEEN 1 AND 3),
          column_position INTEGER NOT NULL CHECK (column_position BETWEEN 1 AND 3),
          UNIQUE (wardrobe_id,row_position,column_position)
        );
        CREATE TABLE IF NOT EXISTS garments (
          id INTEGER PRIMARY KEY,
          name TEXT NOT NULL,
          category TEXT NOT NULL CHECK (category IN ('shirt','pants','dress','jacket','skirt','accessory','other')),
          compartment_id INTEGER REFERENCES compartments(id),
          color TEXT NOT NULL DEFAULT '',
          size TEXT NOT NULL DEFAULT '',
          tag_id TEXT UNIQUE,
          notes TEXT NOT NULL DEFAULT '',
          photo_filename TEXT,
          created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
          updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        CREATE INDEX IF NOT EXISTS garment_compartment ON garments(compartment_id);
        CREATE INDEX IF NOT EXISTS garment_category ON garments(category);
        CREATE TABLE IF NOT EXISTS movements (
          id INTEGER PRIMARY KEY,
          garment_id INTEGER NOT NULL REFERENCES garments(id) ON DELETE CASCADE,
          from_compartment_id INTEGER REFERENCES compartments(id),
          to_compartment_id INTEGER REFERENCES compartments(id),
          changed_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        );
        """)
        conn.execute("INSERT OR IGNORE INTO wardrobes(id,code,name,location) VALUES(1,'W01','My Wardrobe','Bedroom')")
        # Codes A1-C3 represent columns A-C and horizontal tiers 1-3 (top to bottom).
        default_names = [
            ("A1", "Top left shelf", "shelf", 1, 1),
            ("B1", "Top center shelf", "shelf", 1, 2),
            ("C1", "Top right shelf", "shelf", 1, 3),
            ("A2", "Left hanging section", "hanger", 2, 1),
            ("B2", "Center hanging section", "hanger", 2, 2),
            ("C2", "Right shelves", "shelf", 2, 3),
            ("A3", "Left drawer", "drawer", 3, 1),
            ("B3", "Center drawer", "drawer", 3, 2),
            ("C3", "Bottom right shelf", "shelf", 3, 3),
        ]
        conn.executemany("""
        INSERT OR IGNORE INTO compartments(wardrobe_id,code,label,kind,row_position,column_position)
        VALUES(1,?,?,?,?,?)
        """, default_names)


def garment_row(conn, garment_id):
    return conn.execute("""
        SELECT g.*,c.code AS compartment_code,c.label AS compartment_label
        FROM garments g LEFT JOIN compartments c ON g.compartment_id=c.id
        WHERE g.id=?
    """, (garment_id,)).fetchone()