import os
import requests
from typing import Any, Dict, Optional
from django.conf import settings

class WooferAPIError(Exception):
    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        super().__init__(f"Woofer API Error {status_code}")


def _base_url() -> str:
    base = getattr(settings, "WOOFER_API_BASE_URL", "http://127.0.0.1:8000") or "http://127.0.0.1:8000"
    return base.rstrip("/")


def _headers(token: Optional[str] = None) -> Dict[str, str]:
    h: Dict[str, str] = {"Accept": "application/json"}
    dev_user = getattr(settings, "WOOFER_DEV_USER", None)
    if dev_user:
        h["X-Woofer-Dev-User"] = dev_user
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _backend_unreachable_payload(*, url: str, exc: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": "BACKEND_UNREACHABLE",
            "message": "Backend API is unreachable.",
            "details": {
                "exception": exc.__class__.__name__,
                "text": str(exc),
                "url": url,
            },
        },
        "request_id": None,
        "timestamp": None,
    }


def _non_json_payload(*, text: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": {
            "code": "NON_JSON_RESPONSE",
            "message": "API returned non-JSON",
            "details": {"text": text},
        },
        "request_id": None,
        "timestamp": None,
    }


def api_get(path: str, token: Optional[str] = None, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        resp = requests.get(url, headers=_headers(token), params=params, timeout=10)
    except requests.RequestException as e:
        raise WooferAPIError(502, _backend_unreachable_payload(url=url, exc=e))

    try:
        payload: Any = resp.json()
    except Exception:
        payload = _non_json_payload(text=resp.text)

    if resp.status_code >= 400 or (isinstance(payload, dict) and payload.get("ok") is False):
        raise WooferAPIError(resp.status_code, payload)

    return payload  # expected envelope dict


def api_post(path: str, body: dict, token: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        resp = requests.post(url, headers=_headers(token), json=body, timeout=10)
    except requests.RequestException as e:
        raise WooferAPIError(502, _backend_unreachable_payload(url=url, exc=e))

    try:
        payload: Any = resp.json()
    except Exception:
        payload = _non_json_payload(text=resp.text)

    if resp.status_code >= 400 or (isinstance(payload, dict) and payload.get("ok") is False):
        raise WooferAPIError(resp.status_code, payload)

    return payload  # expected envelope dict


def api_put(path: str, json_body: dict, token: Optional[str] = None) -> Dict[str, Any]:
    url = f"{_base_url()}{path}"
    try:
        resp = requests.put(url, headers=_headers(token), json=json_body, timeout=10)
    except requests.RequestException as e:
        raise WooferAPIError(502, _backend_unreachable_payload(url=url, exc=e))

    try:
        payload: Any = resp.json()
    except Exception:
        payload = _non_json_payload(text=resp.text)

    # match GET/POST behavior envelope aware
    if resp.status_code >= 400 or (isinstance(payload, dict) and payload.get("ok") is False):
        raise WooferAPIError(resp.status_code, payload)

    return payload  # expected envelope dict

	

