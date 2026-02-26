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
	then enriches missing AI descriptions.
	
-This will: Fetch provider data, Upsert organizations + pets, Mark missing pets INACTIVE,
	Update last_seen_at, Backfill risk flags | Enrich missing AI descriptions

-Expected output: pets_created / updated, pets_deactivated, risk_backfilled, mode=WRITE

	cd C:\Users\rossm\woofer\backend
	.\.venv\Scripts\Activate.ps1
	python manage.py sync_all --provider rescuegroups --limit 200

#### Override lock (use cautiously)
3.) Use --force only when you are confident no other ingestion is running.

	python manage.py ingest_provider --provider rescuegroups --limit 200 --force --lock-owner manual_override


------------------
##### Smoke checks
-Backend: pets feed (enveloped)
-Expected: top-level ok: true | data.items array | each item has canonical fields (pet_id, name,			organization, etc.)

	curl.exe -H "X-Woofer-Dev-User: web_smoke_user" "http://127.0.0.1:8000/api/v1/pets?limit=5"


---------------------------------------
##### Web Demo Validation (Happy Path)
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

