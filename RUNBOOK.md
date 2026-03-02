# Woofer Runbook (MVP)

This doc describes the canonical operational workflow for keeping pets fresh.

We ingest real RescueGroups listings into canonical models.
We can safely test via dry-run, then run a write sync that refreshes and deactivates stale listings.
The feed reflects real data, risk-adjusted ranking, and controlled application handoff.

-------------------------
## Environment variables

## Backend (`backend/.env.dev` or shell env)
Required for real data:
- `RESCUEGROUPS_API_KEY=...`
Optional / defaults:
- `RESCUEGROUPS_API_BASE_URL=https://api.rescuegroups.org/v5`

Recommended local dev:
- `ENVIRONMENT=dev`
- `DJANGO_DEBUG=1`
- `DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1`

Notifications (MVP stub):
- `WOOFER_NOTIFICATIONS_ENABLED=1`
- `WOOFER_NOTIFICATIONS_FORCE_FAIL=0` (set to 1 to simulate failure paths)

## Web (`web/.env` or shell env)
- `WOOFER_API_BASE_URL=http://127.0.0.1:8000`
- `WOOFER_DEV_USER=web_smoke_user` (optional; sets X-Woofer-Dev-User header for API calls)

_______________________________
### Local dev: start services

### Backend
powershell
cd C:\Users\rossm\woofer\backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8000

### Web
cd C:\Users\rossm\woofer\web
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8001

_________________________________
#### Data refresh workflow (MVP)
-Woofer uses canonical models (Organization, Pet) and ingests via provider adapters.
 RescueGroups ingestion supports dry-run and write modes.
-Provider locking (safety)
 ingest_provider uses a DB lock record (ProviderSyncState) to prevent overlapping runs.
 If you see an error that the provider is locked, 
 it means another run is active (or a prior run crashed).

#### DRY RUN
1.) Sync all (DRY RUN) — safe (no DB writes)
-Exercises full ingestion + enrichment codepaths inside a transaction, then rolls back.

-Expected output: organizations_created | pets_created / updated | pets_deactivated (simulated)
		risk_backfilled | mode=DRY_RUN | No database changes are persisted.

	cd C:\Users\rossm\woofer\backend
	.\.venv\Scripts\Activate.ps1
	python manage.py sync_all --provider rescuegroups --limit 25 --dry-run

#### WRITE
2.) Sync all (WRITE) — real DB writes
Fetches, ingests, deactivates missing pets, backfills risk flags,
**backfills organization geos (ZIP → lat/lon)**, then enriches missing AI descriptions.

-This will:
- Fetch provider data
- Upsert organizations + pets
- Mark missing pets INACTIVE
- Update last_seen_at
- Backfill risk flags
- **Backfill org latitude/longitude from postal_code (geo_source="ZIP")**
- Enrich missing AI descriptions

-Expected output: pets_created / updated, pets_deactivated, risk_backfilled, mode=WRITE

    cd C:\Users\rossm\woofer\backend
    .\.venv\Scripts\Activate.ps1
    python manage.py sync_all --provider rescuegroups --limit 200

Optional:
- Disable geo backfill (rare; useful for debugging):
    python manage.py sync_all --provider rescuegroups --limit 200 --no-backfill-geo


#### Override lock (use cautiously)
3.) Use --force only when you are confident no other ingestion is running.

	python manage.py ingest_provider --provider rescuegroups --limit 200 --force --lock-owner manual_override


---------------------------------------
#### Geocoding (Offline ZIP centroids) 

Woofer now supports deterministic, offline geocoding for Organizations using ZIP centroids.

- Source of truth dataset: `backend/adoption/data/us_zip_centroids.csv`
- Lookup service: `ZipGeoService` (offline, deterministic, no network calls)

When geocoding runs:
- During ingestion/upsert, if an Organization has a valid `postal_code` and is missing lat/lon,
  we resolve ZIP → (lat, lon) from the offline dataset and store:
  - `latitude`, `longitude`
  - `geo_source="ZIP"`
  - `geo_updated_at=now()`

Overwrite rules (safety):
- We DO NOT overwrite existing non-ZIP geocoding.
  If `geo_source` is set to something other than "" or "ZIP", ingestion will leave lat/lon unchanged.

Why this matters:
- Distance filtering in the pets feed depends on org lat/lon for accurate radius filtering.


------------------
##### Smoke checks
-Backend: pets feed (enveloped)
-Expected: top-level ok: true | data.items array | each item has canonical fields (pet_id, name,			organization, etc.)

	curl.exe -H "X-Woofer-Dev-User: web_smoke_user" "http://127.0.0.1:8000/api/v1/pets?limit=5"

##### Geo sanity checks (MVP)
Verify org geos exist after sync_all:

    python manage.py shell
    >>> from adoption.models import Organization
    >>> Organization.objects.filter(latitude__isnull=False, longitude__isnull=False).count()


---------------------------------------
##### Web Demo Validation 
Open:
http://127.0.0.1:8001/

1.) Like a pet
2.) Apply to a pet

Visit:
/applications/
/interests/

Verify applications show:
Pet name - Organization name + location - Status - Submitted timestamp - Apply hint (if present)
 - Continue link (if apply_url exists) - Interests show saved pets list

