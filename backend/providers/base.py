from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, Optional, Protocol, Literal, Any


ProviderName = Literal["rescuegroups", "adoptapet", "petfinder"]


@dataclass(frozen=True)
class ProviderOrg:
    """
    Provider-normalized organization record.
    This is NOT canonical Organization, and must not embed provider-specific schema.
    """
    provider: ProviderName
    external_org_id: str
    name: str
    contact_email: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)  # for debugging/traceability only


@dataclass(frozen=True)
class ProviderPet:
    """
    Provider-normalized pet record.
    This is NOT canonical Pet, and must not embed provider-specific schema.
    """
    provider: ProviderName
    external_pet_id: str
    external_org_id: Optional[str]
    name: str

    # "intent" fields (best-effort - may be None)
    species: Optional[str] = None         # expected "DOG" / "CAT" etc (mapper can normalize)
    age_group: Optional[str] = None       # "PUPPY" / "ADULT" / "SENIOR"
    size: Optional[str] = None            # "S" / "M" / "L" / "XL"
    sex: Optional[str] = None

    breed_primary: Optional[str] = None
    breed_secondary: Optional[str] = None
    is_mixed: Optional[bool] = None

    photos: list[str] = field(default_factory=list)
    raw_description: Optional[str] = None
    listed_at_iso: Optional[str] = None   # keep as ISO string at boundary - mapper parses if desired
    status: Optional[str] = None          # "ACTIVE"/"INACTIVE" or provider status - mapper normalizes

    apply_url: Optional[str] = None
    apply_hint: Optional[str] = None
    
    raw: Dict[str, Any] = field(default_factory=dict)  # traceability only


class ProviderClient(Protocol):
    """
    Provider client interface (adapter boundary).

    Rules:
    - No Django imports required to implement.
    - Must yield ProviderOrg/ProviderPet records.
    - Must not write DB.
    """

    provider_name: ProviderName

    def iter_orgs(self, *, limit: int = 100, org_id: Optional[str] = None) -> Iterator[ProviderOrg]:
        ...

    def iter_pets(self, *, limit: int = 100, org_id: Optional[str] = None) -> Iterator[ProviderPet]:
        ...
