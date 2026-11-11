# Smart Wardrobe ERP - Phase 1 (MVP)

A **working, data-backed web application**, separate from HONGHOUR ERP and KIMHOURR ERP.
Supports Khmer on-screen navigation, Android/iPhone/desktop browsers, one wardrobe (W01), and exactly nine positioned 2D compartments (A1-C3).

## What's built

1. Dashboard: live total, count by garment type, and six recently added items.
2. A **front-elevation 2D plan of one wardrobe** with nine clickable compartments and accurate live counts.
3. Clothing register: add/edit/delete/search/filter; name, category, size, color, notes, optional garment photo and a *manual tag ID* reserved for future RFID.
4. Move clothing between compartments and automatically record a movement log.
5. Settings: edit wardrobe name/location, compartment display names/types.
6. Backup all records **and** uploaded photos as a ZIP; all garment data stored in SQLite.
7. Optional single-owner password login for private hosting.

No real RFID sensor integration yet. No automatic garment detection. No multi-user accounts, payments, stock purchasing, invoicing, or production features. These belong to later phases if needed.

## Windows - quickest way to run it

1. Install Python 3.11+ from https://www.python.org/downloads/ and ensure `Add Python to PATH` is enabled.
2. Unzip the project folder.
3. Double-click **START_SMART_WARDROBE_WINDOWS.bat**. The first launch installs Python libraries once, then opens your browser.
4. Open **http://127.0.0.1:8000** on your Windows computer.
5. Add garments with the green button, then see real counts in the 2D wardrobe.

**Important:** Windows Firewall may ask whether to allow access. For initial testing, allow only private networks if you need your phone to access the app.

## iPhone on the same Wi-Fi (local test only)

To use from a phone while the server is running on a Windows PC:
- Find your Windows computer's local IPv4 address (run `ipconfig`).
- On the iPhone, connected to the same Wi-Fi, open `http://<PC-IPv4-address>:8000` in Safari.
- The desktop Windows program must remain running. For internet access while the PC is off, deploy with proper hosting and persistent storage.

The included `.bat` binds to `0.0.0.0` (other local devices on your network can reach it). It has **no password by default**, so use it only on a trusted private network. To enable password protection, set `SMART_WARDROBE_PASSWORD` and `SESSION_SECRET` before launching. The app does not yet have production-grade account security or rate limiting.

## Manual start (Mac / Linux / Windows terminal)

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. FastAPI documentation is at `/api/docs`.

## Railway deployment notes (not deployed automatically)

Project is **Railway-ready**, but the user must choose a new isolated project and approve any hosting cost.

- Push these files into a **new** GitHub repository such as `smart-wardrobe-erp`. Do not overwrite the existing HONGHOUR / KIMHOURR repositories.
- Create a Railway service from that repository, then create **a persistent Railway volume** mounted at `/data`. Do not rely on the default ephemeral filesystem.
- Set required environment variables:
  - `SMART_WARDROBE_PASSWORD` to a strong, unique owner password
  - `SESSION_SECRET` to a random secret string with at least 32 characters
  - `DATABASE_PATH=/data/wardrobe.sqlite3`
  - `UPLOADS_PATH=/data/uploads`
- The process uses Railway's `$PORT` and offers `GET /health` for health checks.
- Public hosting has ongoing fees. This is an early personal MVP; review authentication, backups, access controls, and security before a production release.

## Data and backups

Local data is at `data/wardrobe.sqlite3`; uploaded images are at `uploads/`.
Use **Settings > Backup** regularly. ZIP backups contain both the database and images. Restore by stopping the server, placing the database into the correct `DATABASE_PATH` folder and photos in `UPLOADS_PATH`, then restarting.

The project does **not** start with imaginary clothing counts or demo items. You add your real garments; dashboard and 2D plan update automatically.

## Test

```bash
pip install pytest httpx
pytest -q
```

## API overview

- `GET /health`
- `GET /api/bootstrap` (dashboard/compartments)
- `GET /api/garments`
- `POST /api/garments` (multipart, image optional)
- `PUT /api/garments/{id}`
- `DELETE /api/garments/{id}`
- `PATCH /api/wardrobe`
- `PATCH /api/compartments/{id}`
- `GET /api/history`
- `GET /api/backup` (complete ZIP)

**Proposed Phase 2:** Build a visual wardrobe compartment editor supporting custom dimensions, widths, and storage configurations. **Phase 3:** RFID/sensor/tag hardware experiments with collision/read-range testing and a tag onboarding flow.