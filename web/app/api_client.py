import os
import requests
from typing import Any, Dict, Optional
from django.conf import settings

API_BASE_URL = os.getenv("WOOFER_API_BASE_URL", "http://127.0.0.1:8000")
DEV_USER = os.getenv("WOOFER_DEV_USER")

class WooferAPIError(Exception):
	def __init__(self, status_code: int, payload: Any):
		self.status_code = status_code
		self.payload = payload
		super().__init__(f"Woofer API Error {status_code}")

def api_get(path: str, token: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{API_BASE_URL}{path}"
    headers = {"Accept": "application/json"}

    if DEV_USER:
            headers["X-Woofer-Dev-User"] = DEV_USER

    if token:
	    headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
    except requests.RequestException as e:
    # Backend unreachable / network error: raise WooferAPIError with envelope-ish payload
            payload = {
                "ok": False,
                "error": {
                    "code": "BACKEND_UNREACHABLE",
                    "message": "Backend API is unreachable.",
                    "details": {
                        "exception": e.__class__.__name__,
                        "text": str(e),
                        "url": url,
                    },
                },
                "request_id": None,
                "timestamp": None,
            }
            raise WooferAPIError(502, payload)

    try:
            payload = resp.json()
    except Exception:
            payload = {
                "ok": False,
                "error": {
                    "code": "NON_JSON_RESPONSE",
                    "message": "API returned non-JSON",
                    "details": {"text": resp.text},
                },
                "request_id": None,
                "timestamp": None,
            }

    if resp.status_code >= 400 or (isinstance(payload, dict) and payload.get("ok") is False):
            raise WooferAPIError(resp.status_code, payload)

    return payload



def api_post(path: str, body: dict):
    url = f"{API_BASE_URL}{path}"
    headers = {"Accept": "application/json"}
    DEV_USER = os.getenv("WOOFER_DEV_USER")
    if DEV_USER:
        headers["X-Woofer-Dev-User"] = DEV_USER

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=10)
    except requests.RequestException as e:
        payload = {
            "ok": False,
            "error": {
                "code": "BACKEND_UNREACHABLE",
                "message": "Backend API is unreachable.",
                "details": {
                    "exception": e.__class__.__name__,
                    "text": str(e),
                    "url": url,
                },
            },
            "request_id": None,
            "timestamp": None,
        }
        raise WooferAPIError(502, payload)

    try:
        payload = resp.json()
    except Exception:
        payload = {
            "ok": False,
            "error": {
                "code": "NON_JSON_RESPONSE",
                "message": "API returned non-JSON",
                "details": {"text": resp.text},
            },
            "request_id": None,
            "timestamp": None,
        }

    if resp.status_code >= 400 or payload.get("ok") is False:
        raise WooferAPIError(resp.status_code, payload)

    return payload

def _headers():
    h = {"Accept": "application/json"}
    dev_user = getattr(settings, "WOOFER_DEV_USER", None)
    if dev_user:
        h["X-Woofer-Dev-User"] = dev_user
    return h

def api_put(path: str, json_body: dict):
    base = settings.WOOFER_API_BASE_URL.rstrip("/")
    url = f"{base}{path}"
    

    resp = requests.put(url, json=json_body, headers=_headers(), timeout=10)
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}

    if resp.status_code >= 400:
        raise WooferAPIError(resp.status_code, payload)
    return payload

	

