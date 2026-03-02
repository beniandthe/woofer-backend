Woofer is an ethical, AI-assisted pet adoption platform designed to reduce bias, prioritize overlooked pets, and simplify the adoption process.

Animal adoption today is fragmented, biased, and overwhelming — it buries shelters in manual work and keeps potential adopters at bay with messy and un-unified applications.  
  Woofer fixes this with a structured, canonical platform that:

- Ingests real provider data (RescueGroups)
- Applies fairness-aware ranking logic
- Surfaces overlooked pets responsibly
- Provides controlled application handoff
- Keeps API responses canonical and enveloped

------------------------------
# Architecture Overview (MVP)

Woofer consists of:

- **Backend (Django + DRF)**
  - Canonical models (`Pet`, `Organization`, `Application`, etc.)
  - Provider ingestion adapters
  - Risk classification + ranking engine
  - Canonical API envelope renderer
  - Controlled application handoff

- **Web (Thin Client)**
  - Calls backend API only
  - No provider schema leakage
  - Displays feed, interests, and applications

# Geocoding (Offline ZIP centroids)
Woofer uses a deterministic offline ZIP centroid dataset to support distance-based filtering:

- Dataset: `backend/adoption/data/us_zip_centroids.csv`
- Service: `ZipGeoService` (offline, no network calls)

Organizations are geocoded from `postal_code` during ingestion and can be backfilled via:
  python manage.py backfill_org_geos

# Real Data Validation (RescueGroups)
Woofer supports ingesting real adoptable pets from RescueGroups into canonical models.

--------------------------------------
## Required Backend Environment Variables
RESCUEGROUPS_API_KEY=...
RESCUEGROUPS_API_BASE_URL=https://api.rescuegroups.org/v5

## Web Environment Variable
WOOFER_API_BASE_URL=http://127.0.0.1:8000

__________________________
### Quick Start (Local Dev)

### Start Backend
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8000

### Start Web
cd web
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8001

### Safe Dry Run (No DB Writes)
cd backend
python manage.py sync_all --provider rescuegroups --limit 25 --dry-run

### Write Sync (Real Ingest + Enrichment)
cd backend
python manage.py sync_all --provider rescuegroups --limit 200

### For operational details see RUNBOOK.md for:
		Environment configuration
		Provider locking behavior
		Dry-run vs write modes
		Lock override safety
		Full demo validation flow

_________________________
#### Canonical Guarantees
Woofer enforces: 
- Enveloped API responses, No provider schema leakage, Deterministic ranking + diversity slotting, Idempotent interest application creation, Controlled application handoff payloads, Audit-safe provider sync state

- Deterministic offline geocoding (ZIP → lat/lon) with geo_source auditing and safe overwrite rules








