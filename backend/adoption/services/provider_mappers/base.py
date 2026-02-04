from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional, Callable, Tuple

from providers.base import ProviderOrg, ProviderPet, ProviderName


# ---------- helpers ----------

def _str(x: Any) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip()
    return s if s else None


def _parse_iso_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _location(city: Optional[str], state: Optional[str]) -> str:
    parts = [p for p in [(_str(city) or None), (_str(state) or None)] if p]
    return ", ".join(parts) if parts else "Unknown"


def _normalize_species(species: Optional[str]) -> str:
    # Canon MVP is DOG; future supports CAT.
    s = (_str(species) or "DOG").upper()
    if s in ("DOG", "CAT"):
        return s
    # Conservative fallback
    return "DOG"


def _normalize_status(status: Optional[str]) -> str:
    # Canon: ACTIVE / INACTIVE
    s = (_str(status) or "").lower()
    if s in ("active", "adoptable", "available"):
        return "ACTIVE"
    if s in ("inactive", "unavailable", "adopted", "pending"):
        return "INACTIVE"
    # Conservative default: keep pets visible unless clearly not adoptable
    return "ACTIVE"


# ---------- canonical dict builders ----------

def canonical_org_dict(org: ProviderOrg) -> Dict[str, Any]:
    """
    Canonical Organization upsert dict:
      key: (source, source_org_id)
    """
    return {
        "source": org.provider.upper(),          # e.g. "RESCUEGROUPS"
        "source_org_id": org.external_org_id,
        "name": org.name or (org.external_org_id or "Unknown Organization"),
        "contact_email": org.contact_email,
        "location": _location(org.city, org.state),
        "is_active": True,
        # raw provider payload should NOT be written to canonical models unless canon says so
    }


def canonical_pet_dict(pet: ProviderPet) -> Dict[str, Any]:
    """
    Canonical Pet upsert dict:
      key: (source, external_id)
    """
    return {
        "source": pet.provider.upper(),          # e.g. "RESCUEGROUPS"
        "external_id": pet.external_pet_id,
        "organization_source_org_id": pet.external_org_id,  # link via (source, source_org_id)
        "name": pet.name or "Unknown",
        "species": _normalize_species(pet.species),
        "age_group": _str(pet.age_group),
        "size": _str(pet.size),
        "sex": _str(pet.sex),
        "breed_primary": _str(pet.breed_primary),
        "breed_secondary": _str(pet.breed_secondary),
        "is_mixed": pet.is_mixed,
        "photos": pet.photos or [],
        "raw_description": _str(pet.raw_description) or "",
        "listed_at": _parse_iso_dt(pet.listed_at_iso),
        "status": _normalize_status(pet.status),
    }


# ---------- registry (for ingest_provider later) ----------

OrgMapper = Callable[[ProviderOrg], Dict[str, Any]]
PetMapper = Callable[[ProviderPet], Dict[str, Any]]

MAPPER_REGISTRY: Dict[ProviderName, Tuple[OrgMapper, PetMapper]] = {
    "rescuegroups": (canonical_org_dict, canonical_pet_dict),
    "adoptapet": (canonical_org_dict, canonical_pet_dict),
    "petfinder": (canonical_org_dict, canonical_pet_dict),
}
