import base64
import json
from datetime import datetime
from typing import Optional, Tuple

def encode_cursor(listed_at: Optional[datetime], pet_id: str) -> str:
    payload = {
        "listed_at": listed_at.isoformat() if listed_at else None,
        "pet_id": pet_id,
    }
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")

def decode_cursor(cursor: str) -> Tuple[Optional[datetime], str]:
    raw = base64.urlsafe_b64decode(cursor.encode("utf-8"))
    payload = json.loads(raw.decode("utf-8"))
    listed_at = payload.get("listed_at")
    pet_id = payload.get("pet_id")
    dt = datetime.fromisoformat(listed_at) if listed_at else None
    return dt, pet_id
