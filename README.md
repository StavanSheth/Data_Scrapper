# Mavon Data Scraper — Slice 1

A local, single-user Business Intelligence Discovery & Entity Normalization application.

## Pipeline Architecture

```
USER INPUT
    ↓
GOOGLE MAPS DISCOVERY (Playwright)
    ↓
RAW GOOGLE RECORDS (Source Audit)
    ↓
DETERMINISTIC NORMALIZATION
    ↓
VALIDATION & PROVENANCE
    ↓
SQLITE (WAL Mode)
    ↓
FASTAPI BACKEND
    ↓
REACT + VITE + TAILWIND FRONTEND
```

---

## Features (Slice 1)

- **Google Maps Discovery**: Autonomous extraction with cookie consent handling, feed scrolling, dynamic card parsing, Place ID and coordinate extraction.
- **Deterministic Normalization**:
  - Name: Unicode NFKD normalization, lowercase, punctuation stripping, configurable legal suffix removal (`pvt ltd`, `llp`, `ltd`, `inc`, `corp`, etc.).
  - Phone: E.164 normalization with Indian regional parsing (`phonenumbers`).
  - URL: Canonical domain extraction, tracking (`utm_*`) parameter removal.
  - Address: Structured component extraction (Street, Locality, City, State, PIN code, Country).
- **SQLite Storage**: Transactional persistence with SQLite WAL mode and foreign keys. Full data retention for `runs`, `source_records`, `businesses`, and `field_provenance`.
- **FastAPI REST API**: Thin controllers with async route handlers, error handling, search, sorting, and pagination.
- **Real-Time Run Monitor**: Live progress tracking via WebSocket with automatic REST polling fallback.
- **Frontend Operator Console**: Sleek dark console layout with Dashboard, Run Monitor, searchable Business Table, and Business Detail Drawer with field-level provenance audit.

---

## Quickstart

### 1. Backend Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Start FastAPI server
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

The API will be available at `http://127.0.0.1:8000/api/health` and docs at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173` in your browser.

---

## Automated Tests

Run the test suite:

```bash
pytest -v
```

All 26 automated unit and integration tests verify normalization, parsing, validation, database operations, pagination, search, API routes, and partial failure handling.
