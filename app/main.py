"""Smart Wardrobe ERP: FastAPI backend, one physical wardrobe, nine compartments."""
import hmac
import io
import os
import secrets
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field
from starlette.middleware.sessions import SessionMiddleware

from . import db as store

ROOT = Path(__file__).resolve().parents[1]
OWNER_PASSWORD = os.getenv("SMART_WARDROBE_PASSWORD", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))
MAX_UPLOAD = 5 * 1024 * 1024
IS_RAILWAY = any(name in os.environ for name in ("RAILWAY_ENVIRONMENT", "RAILWAY_ENVIRONMENT_ID", "RAILWAY_ENVIRONMENT_NAME", "RAILWAY_SERVICE_ID", "RAILWAY_PROJECT_ID"))

if IS_RAILWAY and (not OWNER_PASSWORD or not os.getenv("SESSION_SECRET")):
    raise RuntimeError("Public Railway deployment requires SMART_WARDROBE_PASSWORD and SESSION_SECRET")

store.init_db()
app = FastAPI(title="Smart Wardrobe ERP", version="1.0.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.mount("/static", StaticFiles(directory=ROOT / "app" / "static"), name="static")


def authorized(request: Request):
    return not OWNER_PASSWORD or bool(request.session.get("owner"))


@app.middleware("http")
async def protect_api(request: Request, call_next):
    pathname = request.url.path
    if pathname.startswith("/api/") and pathname not in ("/api/login", "/api/session"):
        if not authorized(request):
            return JSONResponse({"detail": "Please sign in."}, status_code=401)
    if pathname.startswith("/media/") and not authorized(request):
        return JSONResponse({"detail": "Please sign in."}, status_code=401)
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and OWNER_PASSWORD:
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Invalid request origin."}, status_code=403)
    if request.headers.get("content-length") and request.method in ("POST", "PUT"):
        if int(request.headers["content-length"]) > 9 * 1024 * 1024:
            return JSONResponse({"detail": "Request too large."}, status_code=413)
    return await call_next(request)


app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax", https_only=IS_RAILWAY, max_age=60 * 60 * 24 * 7)


class LoginInput(BaseModel):
    password: str


class WardrobeUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)


class CompartmentUpdate(BaseModel):
    label: str = Field(min_length=1, max_length=100)
    kind: str


def clean(value, max_length=120):
    return (value or "").strip()[:max_length]


def require_compartment(conn, compartment_id):
    if compartment_id is None:
        return
    if not conn.execute("SELECT 1 FROM compartments WHERE id=? AND wardrobe_id=1", (compartment_id,)).fetchone():
        raise HTTPException(422, "Unknown compartment.")


def validated_fields(name, category, color, size, tag_id, notes):
    name = clean(name)
    if not name:
        raise HTTPException(422, "Garment name is required.")
    if category not in store.CATEGORIES:
        raise HTTPException(422, "Unknown garment category.")
    tag_id = clean(tag_id, 80) or None
    return name, category, clean(color, 50), clean(size, 30), tag_id, clean(notes, 500)


async def save_photo(upload: UploadFile | None):
    if not upload or not upload.filename:
        return None
    blob = await upload.read(MAX_UPLOAD + 1)
    if len(blob) > MAX_UPLOAD:
        raise HTTPException(413, "Image size must be 5 MB or less.")
    try:
        with Image.open(io.BytesIO(blob)) as image:
            if image.format not in ("JPEG", "PNG", "WEBP"):
                raise HTTPException(422, "Please select a JPG, PNG, or WebP image.")
            image.verify()
        with Image.open(io.BytesIO(blob)) as image:
            if image.width * image.height > 24_000_000:
                raise HTTPException(422, "Image dimensions are too large.")
            image = ImageOps.exif_transpose(image)
            image.thumbnail((1400, 1400))
            if image.mode != "RGB":
                bg = Image.new("RGB", image.size, "white")
                if "A" in image.getbands():
                    bg.paste(image, mask=image.getchannel("A"))
                else:
                    bg.paste(image.convert("RGB"))
                image = bg
            filename = f"{uuid.uuid4().hex}.jpg"
            path = store.UPLOADS_PATH / filename
            image.save(path, format="JPEG", quality=85, optimize=True)
            return filename
    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise HTTPException(422, "Please select a valid JPG, PNG, or WebP image.")


def to_dict(row):
    return dict(row) if row else None


def list_garments(conn, search=None, category=None, compartment=None):
    clauses = []
    vals = []
    if search:
        clauses.append("(g.name LIKE ? OR g.tag_id LIKE ? OR g.color LIKE ?)")
        needle = f"%{search[:80]}%"
        vals.extend((needle, needle, needle))
    if category and category != "all":
        clauses.append("g.category=?")
        vals.append(category)
    if compartment == "unassigned":
        clauses.append("g.compartment_id IS NULL")
    elif compartment and compartment != "all":
        try:
            vals.append(int(compartment))
        except (TypeError, ValueError):
            raise HTTPException(422, "Invalid compartment filter.")
        clauses.append("g.compartment_id=?")
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return [dict(x) for x in conn.execute("""
        SELECT g.*, c.code AS compartment_code, c.label AS compartment_label
        FROM garments g LEFT JOIN compartments c ON c.id=g.compartment_id
    """ + where + " ORDER BY g.created_at DESC,g.id DESC", vals).fetchall()]


@app.get("/")
def home():
    return FileResponse(ROOT / "app" / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "smart-wardrobe-erp"}


@app.get("/api/session")
def get_session(request: Request):
    return {"authenticated": authorized(request), "password_required": bool(OWNER_PASSWORD)}


@app.post("/api/login")
def login(request: Request, body: LoginInput):
    if not OWNER_PASSWORD or hmac.compare_digest(body.password, OWNER_PASSWORD):
        request.session["owner"] = True
        return {"ok": True}
    raise HTTPException(401, "Incorrect password.")


@app.post("/api/logout")
def logout(request: Request):
    request.session.clear()
    return {"ok": True}


@app.get("/api/bootstrap")
def bootstrap():
    with store.db() as conn:
        wardrobe = to_dict(conn.execute("SELECT * FROM wardrobes WHERE id=1").fetchone())
        compartments = [dict(x) for x in conn.execute("""
            SELECT c.*, COUNT(g.id) AS item_count
            FROM compartments c LEFT JOIN garments g ON g.compartment_id=c.id
            GROUP BY c.id ORDER BY c.row_position,c.column_position
        """).fetchall()]
        categories = {c: 0 for c in store.CATEGORIES}
        for row in conn.execute("SELECT category,COUNT(*) AS n FROM garments GROUP BY category"):
            categories[row["category"]] = row["n"]
        unassigned = conn.execute("SELECT COUNT(*) AS n FROM garments WHERE compartment_id IS NULL").fetchone()["n"]
        total = conn.execute("SELECT COUNT(*) AS n FROM garments").fetchone()["n"]
        recent = list_garments(conn)[:6]
        return {"wardrobe": wardrobe, "compartments": compartments, "categories": categories,
                "total": total, "unassigned": unassigned, "recent": recent}


@app.get("/api/garments")
def garments(search: str = "", category: str = "all", compartment: str = "all"):
    with store.db() as conn:
        return list_garments(conn, search, category, compartment)


@app.get("/api/garments/{garment_id}")
def garment_by_id(garment_id: int):
    with store.db() as conn:
        row = store.garment_row(conn, garment_id)
        if row is None:
            raise HTTPException(404, "Garment not found.")
        return dict(row)


@app.post("/api/garments", status_code=201)
async def add_garment(name: str = Form(...), category: str = Form("shirt"),
                      compartment_id: int | None = Form(None), color: str = Form(""),
                      size: str = Form(""), tag_id: str = Form(""), notes: str = Form(""),
                      photo: UploadFile | None = File(None)):
    fields = validated_fields(name, category, color, size, tag_id, notes)
    photo_filename = await save_photo(photo)
    try:
        with store.db() as conn:
            require_compartment(conn, compartment_id)
            result = conn.execute("""
                INSERT INTO garments(name,category,color,size,tag_id,notes,compartment_id,photo_filename)
                VALUES(?,?,?,?,?,?,?,?)
            """, (*fields[:5], fields[5], compartment_id, photo_filename))
            garment_id = result.lastrowid
            conn.execute("INSERT INTO movements(garment_id,to_compartment_id) VALUES(?,?)", (garment_id, compartment_id))
            return dict(store.garment_row(conn, garment_id))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "This tag ID is already assigned to another garment.")
    finally:
        # Preserve uploaded file only for a successfully inserted garment.
        if photo_filename:
            with store.db() as conn:
                exists = conn.execute("SELECT 1 FROM garments WHERE photo_filename=?", (photo_filename,)).fetchone()
            if not exists:
                (store.UPLOADS_PATH / photo_filename).unlink(missing_ok=True)


@app.put("/api/garments/{garment_id}")
async def edit_garment(garment_id: int, name: str = Form(...), category: str = Form("shirt"),
                       compartment_id: int | None = Form(None), color: str = Form(""),
                       size: str = Form(""), tag_id: str = Form(""), notes: str = Form(""),
                       remove_photo: bool = Form(False), photo: UploadFile | None = File(None)):
    fields = validated_fields(name, category, color, size, tag_id, notes)
    new_photo = await save_photo(photo)
    old_photo = None
    success = False
    try:
        with store.db() as conn:
            before = store.garment_row(conn, garment_id)
            if not before:
                raise HTTPException(404, "Garment not found.")
            require_compartment(conn, compartment_id)
            old_photo = before["photo_filename"]
            photo_filename = new_photo if new_photo else (None if remove_photo else old_photo)
            conn.execute("""
                UPDATE garments SET name=?,category=?,color=?,size=?,tag_id=?,notes=?,
                    compartment_id=?,photo_filename=?,updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
                WHERE id=?
            """, (*fields[:5], fields[5], compartment_id, photo_filename, garment_id))
            if before["compartment_id"] != compartment_id:
                conn.execute("""
                    INSERT INTO movements(garment_id,from_compartment_id,to_compartment_id)
                    VALUES(?,?,?)
                """, (garment_id, before["compartment_id"], compartment_id))
            output = dict(store.garment_row(conn, garment_id))
            success = True
        if old_photo and old_photo != output["photo_filename"]:
            (store.UPLOADS_PATH / old_photo).unlink(missing_ok=True)
        return output
    except sqlite3.IntegrityError:
        raise HTTPException(409, "This tag ID is already assigned to another garment.")
    finally:
        if new_photo and not success:
            (store.UPLOADS_PATH / new_photo).unlink(missing_ok=True)


@app.delete("/api/garments/{garment_id}")
def delete_garment(garment_id: int):
    with store.db() as conn:
        garment = store.garment_row(conn, garment_id)
        if not garment:
            raise HTTPException(404, "Garment not found.")
        photo = garment["photo_filename"]
        conn.execute("DELETE FROM garments WHERE id=?", (garment_id,))
    if photo:
        (store.UPLOADS_PATH / photo).unlink(missing_ok=True)
    return {"ok": True}


@app.patch("/api/wardrobe")
def update_wardrobe(body: WardrobeUpdate):
    with store.db() as conn:
        conn.execute("UPDATE wardrobes SET name=?,location=? WHERE id=1", (body.name.strip(), body.location.strip()))
        return to_dict(conn.execute("SELECT * FROM wardrobes WHERE id=1").fetchone())


@app.patch("/api/compartments/{compartment_id}")
def update_compartment(compartment_id: int, body: CompartmentUpdate):
    if body.kind not in store.COMPARTMENT_KINDS:
        raise HTTPException(422, "Unknown compartment kind.")
    with store.db() as conn:
        require_compartment(conn, compartment_id)
        conn.execute("UPDATE compartments SET label=?,kind=? WHERE id=?", (body.label.strip(), body.kind, compartment_id))
        return to_dict(conn.execute("SELECT * FROM compartments WHERE id=?", (compartment_id,)).fetchone())


@app.get("/api/history")
def history():
    with store.db() as conn:
        return [dict(x) for x in conn.execute("""
            SELECT m.id,m.garment_id,g.name AS garment_name,m.changed_at,
                   f.code AS from_code,t.code AS to_code
            FROM movements m JOIN garments g ON m.garment_id=g.id
            LEFT JOIN compartments f ON m.from_compartment_id=f.id
            LEFT JOIN compartments t ON m.to_compartment_id=t.id
            ORDER BY m.id DESC LIMIT 100
        """).fetchall()]


@app.get("/media/{filename}")
def media(filename: str):
    if len(filename) != 36 or not filename.endswith(".jpg") or not all(c in "0123456789abcdef" for c in filename[:32]):
        raise HTTPException(404, "Image not found.")
    path = store.UPLOADS_PATH / filename
    if not path.is_file():
        raise HTTPException(404, "Image not found.")
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})


@app.get("/api/backup")
def backup():
    """Full offline backup with a consistent SQLite snapshot and garment photos."""
    with tempfile.TemporaryDirectory() as tmpdir:
        snapshot = Path(tmpdir) / "wardrobe.sqlite3"
        original = store.connection()
        try:
            with sqlite3.connect(snapshot) as dst:
                original.backup(dst)
        finally:
            original.close()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(snapshot, "data/wardrobe.sqlite3")
            for image in store.UPLOADS_PATH.glob("*.jpg"):
                archive.write(image, f"uploads/{image.name}")
            archive.writestr("RESTORE.txt", "Stop the app, copy data/wardrobe.sqlite3 and uploads/ into the app folder, then restart.\n")
        return Response(stream.getvalue(), media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="smart_wardrobe_backup.zip"'})