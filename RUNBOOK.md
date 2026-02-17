# Woofer Runbook (MVP)

This doc describes the canonical operational workflow for keeping pets fresh.

## Local dev: start services

### Backend
powershell
cd C:\Users\rossm\woofer\backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8000

### Web
cd C:\Users\rossm\woofer\web
.\.venv\Scripts\Activate.ps1
python manage.py runserver 8001

### Data refresh workflow (MVP)
1) Ingest provider data (WRITE)
cd C:\Users\rossm\woofer\backend
.\.venv\Scripts\Activate.ps1
python manage.py ingest_provider --provider rescuegroups --limit 200

2) Enrich missing AI descriptions (WRITE)
cd C:\Users\rossm\woofer\backend
.\.venv\Scripts\Activate.ps1
python manage.py enrich_pets --limit 200

### Smoke checks
Backend: pets feed (enveloped)
curl.exe -H "X-Woofer-Dev-User: web_smoke_user" "http://127.0.0.1:8000/api/v1/pets?limit=5"

### Sync all (DRY RUN)
cd C:\Users\rossm\woofer\backend
.\.venv\Scripts\Activate.ps1
python manage.py sync_all --provider rescuegroups --limit 25 --dry-run

### Sync all (WRITE)
python manage.py sync_all --provider rescuegroups --limit 200


