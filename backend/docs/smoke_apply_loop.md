# Smoke Test — Apply Loop (v1)

## Prereqs
- Backend running on :8000
- Web running on :8001
- A dev user header exists for web -> backend calls
- At least 1 ACTIVE pet exists in DB
- Pet.apply_url may or may not exist (both cases should be handled)

## Run servers

### Terminal A (backend)
python manage.py runserver 8000

### Terminal B (web)
python manage.py runserver 8001

---

## Smoke Flow (Web)

### 1) Open web home
Visit:
http://127.0.0.1:8001/

Expected:
- A list of pets renders
- Each pet shows Like + Apply buttons

### 2) Like a pet
Click Like on any pet.

Expected:
- Redirect back to /?msg=liked (or already_liked)
- Backend receives:
  POST /api/v1/pets/{pet_id}/interest  -> 200
- Web shows the pet as liked (UI dependent)

### 3) Apply for a pet
Click Apply on any pet.

Expected:
- Backend receives:
  POST /api/v1/pets/{pet_id}/apply -> 200
- Web renders confirmation page:
  "Email sent to the organization."
  "This is not an approval. The rescue will contact you directly."
- If apply_url present:
  Show "Continue to organization application" button/link
- If apply_url missing:
  Show message that no external link was provided
- Always show "Return home"

---

## Smoke Flow (API)

### 4) Feed endpoint is enveloped
curl -H "X-Woofer-Dev-User: web_smoke_user" "http://127.0.0.1:8000/api/v1/pets?limit=5"

Expected JSON shape:
{
  "ok": true,
  "data": { "items": [...], "next_cursor": ... },
  "meta": {},
  "request_id": "...",
  "timestamp": "..."
}

### 5) Apply endpoint is enveloped
curl.exe --% -H "X-Woofer-Dev-User: web_smoke_user" -H "Content-Type: application/json" -d "{\"payload\":{}}" "http://127.0.0.1:8000/api/v1/pets/{PET_UUID}/apply"

Expected JSON shape:
{
  "ok": true,
  "data": {
    "application_id": "...",
    "pet_id": "...",
    "organization_id": "...",
    "email_status": "SENT|FAILED",
    "payload": {},
    "apply_url": "...",
    "apply_hint": "...",
    "created_at": "..."
  },
  "meta": {},
  "request_id": "...",
  "timestamp": "..."
}
