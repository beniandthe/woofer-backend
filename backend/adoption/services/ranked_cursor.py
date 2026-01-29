import base64
import json
from typing import Optional, Tuple

def encode_rank_cursor(score: float, pet_id: str) -> str:
    payload = {"score": score, "pet_id": pet_id}
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")

def decode_rank_cursor(cursor: str) -> Tuple[float, str]:
    raw = base64.urlsafe_b64decode(cursor.encode("utf-8"))
    payload = json.loads(raw.decode("utf-8"))
    return float(payload["score"]), payload["pet_id"]
