# Smart Wardrobe ERP 1.1.0

Room Planner + Wardrobe Compartments + Real Clothing Photo Gallery.

## Workflow

Open Layout, then Edit plan: (1) define the room, (2) position and size W01, (3) divide and size compartments. Save. Click W01 in the room, click a compartment, then click an uploaded garment photo to see the large image and details.

## Included

- One room and one wardrobe; rectangle/square or bottom-right-cut L-shaped room.
- Room width, depth and height in millimetres; door/window wall, offset and width.
- Wardrobe width, height, depth, X/Y position, 0/90-degree rotation and drag placement.
- Variable compartment rectangles, individual millimetre dimensions/positions, split horizontally/vertically, codes, labels, and hanging/shelf/drawer/box types. Maximum 80 compartments.
- Real uploaded-photo gallery per compartment, search and category filter, two columns on phones.
- Large garment image, zoom, previous/next garment, details, edit, move, and delete confirmation.
- Photo-file picker, camera capture hint and upload preview. Existing JPG/PNG/WebP 5 MB limit remains; native HEIC is not supported.
- Protected planner API; atomic saves, revision conflict checks, overlap/bounds validation.

## Preservation and migration

Startup makes a SQLite snapshot under the database's `backups` directory before the first geometry migration. The migration preserves wardrobe, garment and compartment IDs and movement records; uploaded photo files are not modified. Repeated startups do not recreate removed empty compartments. Compartments with clothing or movement history cannot be removed. Splitting keeps existing clothing in the original half; use Move to redistribute it.

The initial room and wardrobe measurements are editable starter values, not verified measurements of the owner's actual room. This is an inventory/location planner, not manufacturing CAD: panel thickness, hardware, arbitrary polygons, door-swing clearances and construction dimensions are not modelled. RFID integration remains a later phase.

## Verification

21 automated tests passed locally, including legacy-data migration, photos, counts, movement history, login guards, invalid geometry, stale saves and compartment splitting. Chromium viewport checks cover mobile layout, garment creation/photo display, details, editing, splitting and saving. No test clothing or generated mockup imagery is seeded into production.

## Deployment

Use the existing Railway service and persistent `/data` volume; keep `DATABASE_PATH`, `UPLOADS_PATH`, `SMART_WARDROBE_PASSWORD` and `SESSION_SECRET` unchanged. `/health` reports version 1.1.0. No additional paid services are required by this change.
