from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


# Canonical "source" string used everywhere internally
SOURCE_PETFINDER = "PETFINDER"


def _str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _bool(x: Any, default: bool = False) -> bool:
    if x is None:
        return default
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.strip().lower() in ("1", "true", "yes", "y")
    return bool(x)


def _list(x: Any) -> List[Any]:
    if x is None:
        return []
    if isinstance(x, list):
        return x
    return [x]


def _parse_iso_dt(x: Any) -> Optional[datetime]:
    """
    Petfinder often returns ISO-8601 strings.
    Keep parsing conservative; if parsing fails, return None.
    """
    s = _str(x)
    if not s:
        return None
    try:
        # handles "2026-01-01T12:34:56+00:00"
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def map_petfinder_org_to_canonical(org: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a dict shaped for Organization upsert.
    Does not write to DB.
    """
    # Petfinder org "id" is typically like "CA123"
    source_org_id = _str(org.get("id"))

    name = _str(org.get("name"))
    contact = org.get("contact")
    if not isinstance(contact, dict):
        contact = {}
    email = _str(org.get("email") or contact.get("email"))


    address = org.get("address") or {}
    city = _str(address.get("city"))
    state = _str(address.get("state"))
    location = ", ".join([p for p in [city, state] if p]) if (city or state) else None

    return {
        "source": SOURCE_PETFINDER,
        "source_org_id": source_org_id,
        "name": name or (source_org_id or "Unknown Organization"),
        "contact_email": email,
        "location": location or "Unknown",
        "is_active": True,
    }


def map_petfinder_pet_to_canonical(animal: Dict[str, Any], organization_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Returns a dict shaped for Pet upsert.
    organization_id here is the external Petfinder org id (e.g. "CA123") if present.
    Does not write to DB.
    """
    external_id = _str(animal.get("id"))
    name = _str(animal.get("name")) or "Unknown"

    species_raw = _str(animal.get("species")) or "DOG"
    # Canon MVP: DOG; future: CAT. Map conservatively.
    species = "DOG" if species_raw.upper() not in ("CAT",) else "CAT"

    # Photos is usually a list of dicts with "full"/"large"/"medium"/"small"
    photos: List[str] = []
    for p in _list(animal.get("photos")):
        if isinstance(p, dict):
            # Prefer "full", fallback to "large", etc.
            url = _str(p.get("full")) or _str(p.get("large")) or _str(p.get("medium")) or _str(p.get("small"))
            if url:
                photos.append(url)

    raw_description = _str(animal.get("description")) or ""
    listed_at = _parse_iso_dt(animal.get("published_at"))

    # Petfinder "status" can be "adoptable", "adopted", etc.
    pf_status = _str(animal.get("status")) or "adoptable"
    status = "ACTIVE" if pf_status.lower() == "adoptable" else "INACTIVE"

    org_id = _str(organization_id) or _str(animal.get("organization_id"))

    return {
        "source": SOURCE_PETFINDER,
        "external_id": external_id,
        "organization_source_org_id": org_id,  # for lookup during ingestion
        "name": name,
        "species": species,
        "photos": photos,
        "raw_description": raw_description,
        "listed_at": listed_at,
        "status": status,
    }
