"""Room, single wardrobe and freely sized compartments (millimetres/percent)."""
import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from . import db as store


class Model(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)


class Opening(Model):
    kind: Literal['door', 'window'] = 'door'
    wall: int = Field(ge=0, le=5)
    offset: float = Field(ge=0, le=30000)
    width: float = Field(ge=100, le=6000)


class Room(Model):
    name: str = Field(min_length=1, max_length=100)
    shape: Literal['rectangle', 'l'] = 'rectangle'
    width: float = Field(ge=1000, le=30000)
    depth: float = Field(ge=1000, le=30000)
    height: float = Field(ge=1000, le=8000)
    cut_width: float = Field(default=1000, ge=100, le=29000)
    cut_depth: float = Field(default=1000, ge=100, le=29000)
    openings: list[Opening] = Field(default_factory=list, max_length=16)


class Cabinet(Model):
    width: float = Field(ge=200, le=12000)
    height: float = Field(ge=200, le=8000)
    depth: float = Field(ge=100, le=2000)
    x: float = Field(ge=0, le=30000)
    y: float = Field(ge=0, le=30000)
    rotation: Literal[0, 90] = 90


class Cell(Model):
    id: int | None = Field(default=None, ge=1)
    code: str = Field(min_length=1, max_length=16, pattern=r'^[A-Za-z0-9_-]+$')
    label: str = Field(min_length=1, max_length=100)
    kind: Literal['hanger', 'shelf', 'drawer', 'box']
    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    w: float = Field(ge=1, le=100)
    h: float = Field(ge=1, le=100)


class Plan(Model):
    revision: int = Field(ge=0)
    room: Room
    cabinet: Cabinet
    compartments: list[Cell] = Field(min_length=1, max_length=80)


def vertices(room):
    w, d = room['width'], room['depth']
    if room['shape'] == 'rectangle':
        return [(0, 0), (w, 0), (w, d), (0, d)]
    cw, cd = room['cut_width'], room['cut_depth']
    return [(0, 0), (w, 0), (w, d-cd), (w-cw, d-cd), (w-cw, d), (0, d)]


def validate_plan(plan):
    r, w, cells = plan['room'], plan['cabinet'], plan['compartments']
    if not r['name'].strip():
        raise HTTPException(422, 'Room name is required.')
    if r['shape'] == 'l' and (r['cut_width'] >= r['width'] or r['cut_depth'] >= r['depth']):
        raise HTTPException(422, 'The L-shape cut-out must be smaller than the room.')
    fw, fd = (w['depth'], w['width']) if w['rotation'] == 90 else (w['width'], w['depth'])
    if w['x']+fw > r['width']+0.01 or w['y']+fd > r['depth']+0.01 or w['height'] > r['height']:
        raise HTTPException(422, 'The wardrobe must fit inside the room, including its height.')
    if r['shape'] == 'l' and w['x']+fw > r['width']-r['cut_width']+0.01 and w['y']+fd > r['depth']-r['cut_depth']+0.01:
        raise HTTPException(422, 'The wardrobe overlaps the L-shape cut-out.')
    pts = vertices(r)
    for i, o in enumerate(r['openings']):
        if o['wall'] >= len(pts):
            raise HTTPException(422, 'Opening wall does not exist in this room shape.')
        a, b = pts[o['wall']], pts[(o['wall']+1) % len(pts)]
        length = abs(a[0]-b[0])+abs(a[1]-b[1])
        if o['offset']+o['width'] > length+0.01:
            raise HTTPException(422, 'Door/window extends past its wall.')
        for prev in r['openings'][:i]:
            if o['wall'] == prev['wall'] and min(o['offset']+o['width'], prev['offset']+prev['width']) > max(o['offset'], prev['offset'])+0.01:
                raise HTTPException(422, 'Doors/windows on the same wall cannot overlap.')
    ids = [c['id'] for c in cells if c['id'] is not None]
    if len(ids) != len(set(ids)) or len({c['code'].upper() for c in cells}) != len(cells):
        raise HTTPException(422, 'Compartment IDs and codes must be unique.')
    for i, c in enumerate(cells):
        if c['code'].startswith('__'):
            raise HTTPException(422, 'Codes starting with __ are reserved.')
        if not c['label'].strip() or c['x']+c['w'] > 100.01 or c['y']+c['h'] > 100.01:
            raise HTTPException(422, 'Each compartment needs a name and must fit inside the wardrobe.')
        for p in cells[:i]:
            if min(c['x']+c['w'], p['x']+p['w']) > max(c['x'], p['x'])+0.01 and min(c['y']+c['h'], p['y']+p['h']) > max(c['y'], p['y'])+0.01:
                raise HTTPException(422, 'Compartments cannot overlap. Adjust their positions/sizes.')


def migrate():
    """Keep all IDs/garment links; snapshot before replacing the nine-slot table."""
    conn = store.connection()
    try:
        cols = {r['name'] for r in conn.execute('PRAGMA table_info(compartments)')}
        if 'x' not in cols:
            backup_dir = store.DB_PATH.parent / 'backups'
            backup_dir.mkdir(exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
            with sqlite3.connect(backup_dir / f'pre_v1_1_{stamp}.sqlite3') as snapshot:
                conn.backup(snapshot)
            conn.execute('PRAGMA foreign_keys=OFF')
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('''CREATE TABLE compartments_v11 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wardrobe_id INTEGER NOT NULL REFERENCES wardrobes(id),
                code TEXT NOT NULL UNIQUE, label TEXT NOT NULL,
                kind TEXT NOT NULL CHECK(kind IN ('hanger','shelf','drawer','box')),
                row_position INTEGER NOT NULL, column_position INTEGER NOT NULL,
                x REAL NOT NULL, y REAL NOT NULL, w REAL NOT NULL, h REAL NOT NULL)''')
            conn.execute('''INSERT INTO compartments_v11
                SELECT id,wardrobe_id,code,label,kind,row_position,column_position,
                    (column_position-1)*100.0/3,
                    CASE row_position WHEN 1 THEN 0 WHEN 2 THEN 25 ELSE 80 END,
                    100.0/3, CASE row_position WHEN 1 THEN 25 WHEN 2 THEN 55 ELSE 20 END
                FROM compartments''')
            conn.execute('DROP TABLE compartments')
            conn.execute('ALTER TABLE compartments_v11 RENAME TO compartments')
            if conn.execute('PRAGMA foreign_key_check').fetchall():
                raise RuntimeError('Migration foreign key validation failed')
            conn.commit()
            conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('''CREATE TABLE IF NOT EXISTS planner_config (
            id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL DEFAULT 0,
            document TEXT NOT NULL)''')
        defaults = {
            'room': {'name':conn.execute('SELECT location FROM wardrobes WHERE id=1').fetchone()[0],'shape':'rectangle','width':4000,'depth':3000,'height':2700,
                     'cut_width':1000,'cut_depth':1000,
                     'openings':[{'kind':'door','wall':2,'offset':1400,'width':800},
                                 {'kind':'window','wall':0,'offset':1200,'width':1400}]},
            'cabinet': {'width':2400,'height':2400,'depth':600,'x':3400,'y':300,'rotation':90}}
        conn.execute('INSERT OR IGNORE INTO planner_config(id,document) VALUES(1,?)', (json.dumps(defaults),))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def read_plan(conn):
    row = conn.execute('SELECT * FROM planner_config WHERE id=1').fetchone()
    result = json.loads(row['document'])
    result['revision'] = row['revision']
    result['compartments'] = [dict(r) for r in conn.execute('''SELECT c.id,c.code,c.label,c.kind,
        c.x,c.y,c.w,c.h FROM compartments c ORDER BY c.y,c.x,c.id''')]
    return result


def install(app):
    @app.get('/api/planner')
    def get_planner():
        with store.db() as conn:
            return read_plan(conn)

    @app.put('/api/planner')
    def save_planner(body: Plan):
        plan = body.model_dump()
        validate_plan(plan)
        with store.db() as conn:
            conn.execute('BEGIN IMMEDIATE')
            previous = read_plan(conn)
            if previous['revision'] != plan['revision']:
                raise HTTPException(409, 'The plan changed in another window. Reload before saving.')
            existing = {c['id'] for c in previous['compartments']}
            incoming = {c['id'] for c in plan['compartments'] if c['id'] is not None}
            if not incoming <= existing:
                raise HTTPException(422, 'Unknown compartment ID.')
            for cid in existing-incoming:
                used = conn.execute('SELECT 1 FROM garments WHERE compartment_id=?', (cid,)).fetchone()
                history = conn.execute('SELECT 1 FROM movements WHERE from_compartment_id=? OR to_compartment_id=?', (cid,cid)).fetchone()
                if used or history:
                    raise HTTPException(409, 'Cannot remove a compartment with clothing or movement history. Resize it instead.')
                conn.execute('DELETE FROM compartments WHERE id=?', (cid,))
            # Temporary codes allow safe swaps without changing stable IDs.
            for cid in incoming:
                conn.execute('UPDATE compartments SET code=? WHERE id=?', (f'__v11_{cid}',cid))
            for i, c in enumerate(plan['compartments']):
                values = (c['code'].upper(),c['label'].strip(),c['kind'],i+1,1,c['x'],c['y'],c['w'],c['h'])
                if c['id'] is None:
                    conn.execute('''INSERT INTO compartments(wardrobe_id,code,label,kind,row_position,column_position,x,y,w,h)
                        VALUES(1,?,?,?,?,?,?,?,?,?)''', values)
                else:
                    conn.execute('''UPDATE compartments SET code=?,label=?,kind=?,row_position=?,column_position=?,x=?,y=?,w=?,h=?
                        WHERE id=?''', (*values,c['id']))
            document = json.dumps({'room':plan['room'],'cabinet':plan['cabinet']})
            conn.execute('UPDATE planner_config SET document=?,revision=revision+1 WHERE id=1', (document,))
            conn.execute('UPDATE wardrobes SET location=? WHERE id=1', (plan['room']['name'].strip(),))
            return read_plan(conn)

    class MoveInput(Model):
        compartment_id: int | None = Field(default=None, ge=1)

    @app.patch('/api/garments/{garment_id}/move')
    def move_garment(garment_id: int, body: MoveInput):
        with store.db() as conn:
            old = store.garment_row(conn, garment_id)
            if not old:
                raise HTTPException(404, 'Garment not found.')
            cid = body.compartment_id
            if cid is not None and not conn.execute('SELECT 1 FROM compartments WHERE id=? AND wardrobe_id=1', (cid,)).fetchone():
                raise HTTPException(422, 'Unknown compartment.')
            if old['compartment_id'] != cid:
                conn.execute("UPDATE garments SET compartment_id=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?", (cid,garment_id))
                conn.execute('INSERT INTO movements(garment_id,from_compartment_id,to_compartment_id) VALUES(?,?,?)',
                             (garment_id,old['compartment_id'],cid))
            return dict(store.garment_row(conn, garment_id))
