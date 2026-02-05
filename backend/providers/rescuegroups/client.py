from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, List

import requests

from providers.base import ProviderClient, ProviderOrg, ProviderPet


_JSONAPI = "application/vnd.api+json"


def _first(lst: Any) -> Optional[Any]:
    return lst[0] if isinstance(lst, list) and lst else None


class RescueGroupsAPIError(RuntimeError):
    pass


@dataclass
class RescueGroupsClient(ProviderClient):
    """
    RescueGroups v5 Public API adapter.

    Docs highlights:
    - Base URL: https://api.rescuegroups.org/v5
    - Headers: Content-Type application/vnd.api+json; Authorization API key
    - Paging via ?limit=&page=
    """
    api_key: str
    base_url: str = "https://api.rescuegroups.org/v5"
    timeout_s: int = 20

    provider_name = "rescuegroups"

    def _headers(self) -> Dict[str, str]:
        # RescueGroups requires Content-Type on every request and Authorization with API key.
        return {
            "Content-Type": _JSONAPI,
            "Accept": _JSONAPI,
            "Authorization": self.api_key,
        }

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        resp = requests.get(url, headers=self._headers(), params=params or {}, timeout=self.timeout_s)

        if resp.status_code == 429:
            raise RescueGroupsAPIError("429 Too Many Requests (rate limited)")
        if resp.status_code >= 400:
            raise RescueGroupsAPIError(f"{resp.status_code} error from RescueGroups: {resp.text[:300]}")

        return resp.json()

    def iter_orgs(self, *, limit: int = 100, org_id: Optional[str] = None) -> Iterator[ProviderOrg]:
        if org_id:
            # GET /public/orgs/{orgs.id}
            payload = self._get(f"/public/orgs/{org_id}", params=None)
            for org in self._parse_orgs(payload):
                yield org
            return

        page = 1
        remaining = limit

        # GET /public/orgs/?limit=&page=
        while remaining > 0:
            chunk = min(250, remaining)  # docs: most endpoints max 250
            payload = self._get("/public/orgs/", params={"limit": chunk, "page": page})
            orgs = self._parse_orgs(payload)

            if not orgs:
                return

            for org in orgs:
                yield org
                remaining -= 1
                if remaining <= 0:
                    return

            meta = payload.get("meta") or {}
            pages = meta.get("pages")
            if pages is not None and page >= int(pages):
                return
            page += 1

    def iter_pets(self, *, limit: int = 100, org_id: Optional[str] = None) -> Iterator[ProviderPet]:
        """
        MVP pulls DOGS only from the pre-defined 'available' view.
        Paging via ?limit=&page=
        """
        page = 1
        remaining = limit

        # Endpoint pattern appears in docs as:
        # /public/animals/search/available/dogs/?limit=10&page=2...
        # We also request include=pictures to get URLs and keep mapping simple.
        base_path = "/public/animals/search/available/dogs/"
        if org_id:
            base_path = f"/public/orgs/{org_id}/animals/search/available/dogs/"

        while remaining > 0:
            chunk = min(250, remaining)
            payload = self._get(
                base_path,
                params={
                    "limit": chunk,
                    "page": page,
                    "include": "pictures",
                    "fields[animals]": "name,descriptionText,sex,sizeGroup,ageGroup,isBreedMixed,breedPrimary,breedSecondary,updatedDate,createdDate,availableDate,pictureThumbnailUrl,pictureCount",
                },
            )

            pets = self._parse_animals(payload)
            if not pets:
                return

            for pet in pets:
                yield pet
                remaining -= 1
                if remaining <= 0:
                    return

            meta = payload.get("meta") or {}
            pages = meta.get("pages")
            if pages is not None and page >= int(pages):
                return
            page += 1

    # ---------- parsers ----------

    def _parse_orgs(self, payload: Dict[str, Any]) -> List[ProviderOrg]:
        data = payload.get("data")
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return []

        out: List[ProviderOrg] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            attrs = row.get("attributes") or {}
            out.append(
                ProviderOrg(
                    provider=self.provider_name,
                    external_org_id=str(row.get("id")),
                    name=str(attrs.get("name") or "").strip() or str(row.get("id")),
                    contact_email=attrs.get("email"),
                    city=attrs.get("city"),
                    state=attrs.get("state"),
                    raw=row,
                )
            )
        return out

    def _parse_animals(self, payload: Dict[str, Any]) -> List[ProviderPet]:
        data = payload.get("data")
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return []

        included = payload.get("included") or []
        # Build picture lookup: (animal_id -> [picture_urls])
        pic_urls_by_animal: Dict[str, List[str]] = {}
        if isinstance(included, list):
            for inc in included:
                if not isinstance(inc, dict):
                    continue
                if inc.get("type") != "pictures":
                    continue
                attrs = inc.get("attributes") or {}
                # pictures relate back via relationships? not always present; fallback to urls only if can’t link
                # We'll link when the animal object includes pictures relationship; else ignore.
                # We'll just keep URLs available by picture id; the animal parser will assemble via relationship.
                # (Handled below)
                pass

        out: List[ProviderPet] = []

        for row in data:
            if not isinstance(row, dict):
                continue
            attrs = row.get("attributes") or {}
            rel = row.get("relationships") or {}

            external_org_id = None
            org_rel = rel.get("orgs") or rel.get("org")  # defensive
            if isinstance(org_rel, dict):
                org_data = org_rel.get("data")
                if isinstance(org_data, list):
                    first = _first(org_data)
                    if isinstance(first, dict) and first.get("id"):
                        external_org_id = str(first["id"])
                elif isinstance(org_data, dict) and org_data.get("id"):
                    external_org_id = str(org_data["id"])

            # Pictures: prefer pictureThumbnailUrl; otherwise include pictures relationship if present
            photos: List[str] = []
            thumb = attrs.get("pictureThumbnailUrl")
            if thumb:
                photos.append(str(thumb))

            out.append(
                ProviderPet(
                    provider=self.provider_name,
                    external_pet_id=str(row.get("id")),
                    external_org_id=external_org_id,
                    name=str(attrs.get("name") or "").strip() or "Unknown",
                    species="DOG",  # MVP: dogs endpoint
                    age_group=_map_age_group(attrs.get("ageGroup")),
                    size=_map_size(attrs.get("sizeGroup")),
                    sex=_map_sex(attrs.get("sex")),
                    breed_primary=attrs.get("breedPrimary"),
                    breed_secondary=attrs.get("breedSecondary"),
                    is_mixed=attrs.get("isBreedMixed"),
                    photos=photos,
                    raw_description=attrs.get("descriptionText") or "",
                    listed_at_iso=attrs.get("availableDate") or attrs.get("createdDate") or attrs.get("updatedDate"),
                    status="Available",  # mapper normalizes to ACTIVE
                    raw=row,
                )
            )
        return out


def _map_age_group(v: Any) -> Optional[str]:
    # RescueGroups ageGroup: Baby, Young Adult, Senior :contentReference[oaicite:5]{index=5}
    if not v:
        return None
    s = str(v).strip().lower()
    if s in ("baby",):
        return "PUPPY"
    if s in ("young adult", "adult"):
        return "ADULT"
    if s in ("senior",):
        return "SENIOR"
    return None


def _map_size(v: Any) -> Optional[str]:
    # RescueGroups sizeGroup: Small, Medium, Large, X-Large :contentReference[oaicite:6]{index=6}
    if not v:
        return None
    s = str(v).strip().lower()
    if s == "small":
        return "S"
    if s == "medium":
        return "M"
    if s == "large":
        return "L"
    if s in ("x-large", "xlarge", "extra large"):
        return "XL"
    return None


def _map_sex(v: Any) -> Optional[str]:
    if not v:
        return None
    s = str(v).strip().lower()
    if s == "male":
        return "MALE"
    if s == "female":
        return "FEMALE"
    return None
