import os
import requests
from typing import Any, Dict, Optional

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

	resp = requests.get(url, headers=headers, params=params, timeout=10)

	try:
		payload = resp.json()
	except Exception:
		payload = {
			"ok": False,
			"error": {"code": "NON_JSON_RESPONSE", "message": "API returned non-JSON", "details": {"text": resp.text}},
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

	resp = requests.post(url, headers=headers, json=body, timeout=10)
	payload = resp.json()

	if resp.status_code >= 400 or payload.get("ok") is False:
		raise WooferAPIError(resp.status_code, payload)

	return payload	

	

	

