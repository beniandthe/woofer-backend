from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import requests
from providers.base import ProviderClient, ProviderOrg, ProviderPet


_JSONAPI = "application/vnd.api+json"


def _first(lst: Any) -> Optional[Any]:
    return lst[0] if isinstance(lst, list) and lst else None


def _upgrade_img_width(url: str, width: int = 800) -> str:
    """
    RescueGroups picture URLs often come with ?width=100.
    For web card display, store a larger width to avoid blur.
    """
    try:
        parts = urlparse(url)
        qs = parse_qs(parts.query)
        qs["width"] = [str(int(width))]
        new_query = urlencode(qs, doseq=True)
        return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))
    except Exception:
        return url
 
def _pick_picture_url(attrs: Dict[str, Any]) -> Optional[str]:
    """
    RescueGroups included pictures commonly use dicts:
      attrs["large"] = {"url": "...", "resolutionX": ..., ...}
    Sometimes they may be strings. Support both.
    Prefer large, then original, then small.
    """
    if not isinstance(attrs, dict):
        return None

    for k in ("large", "original", "small"):
        v = attrs.get(k)

        # string form
        if isinstance(v, str) and v.strip():
            return v.strip()

        # dict form
        if isinstance(v, dict):
            url = v.get("url") or v.get("uri") or v.get("href")
            if isinstance(url, str) and url.strip():
                return url.strip()

    return None

def _dedupe_keep_order(urls: List[str]) -> List[str]:
    seen = set()
    out = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out

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
            chunk = min(250, remaining)  # docs - most endpoints max 250
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

        # Endpoint pattern appears in docs as
        # /public/animals/search/available/dogs/?limit=10&page=2...
        # also request include=pictures to get URLs and keep mapping simple
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
                    "include": "pictures,orgs",
                    "fields[animals]": "name,descriptionText,sex,sizeGroup,ageGroup,isBreedMixed,breedPrimary,breedSecondary,updatedDate,createdDate,availableDate,pictureThumbnailUrl,pictureCount,orgs,pictures", 
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

    # parsers 

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
            postal = (
                attrs.get("postalcode")
                or attrs.get("postalCode")
                or attrs.get("postal_code")
                or attrs.get("zip")
                or attrs.get("zipcode")
                or attrs.get("postal")
            )
            out.append(
                ProviderOrg(
                    provider=self.provider_name,
                    external_org_id=str(row.get("id")),
                    name=str(attrs.get("name") or "").strip() or str(row.get("id")),
                    contact_email=attrs.get("email"),
                    city=attrs.get("city"),
                    state=attrs.get("state"),
                    postal_code=str(postal).strip() if postal else None,
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

        pic_meta_by_id: Dict[str, tuple[int, str]] = {}

        if isinstance(included, list):
            for inc in included:
                if not isinstance(inc, dict):
                    continue
                if inc.get("type") != "pictures":
                    continue
                pic_id = str(inc.get("id") or "").strip()
                if not pic_id:
                    continue

                attrs = inc.get("attributes") or {}
                url = _pick_picture_url(attrs)
                if not url:
                    continue

                # default order high if missing
                try:
                    order = int(attrs.get("order") or 9999)
                except (TypeError, ValueError):
                    order = 9999

                pic_meta_by_id[pic_id] = (order, _upgrade_img_width(url, width=800))

        out: List[ProviderPet] = []

        for row in data:
            if not isinstance(row, dict):
                continue
            attrs = row.get("attributes") or {}
            rel = row.get("relationships") or {}

            # org id extraction unchanged...
            external_org_id = None
            org_rel = (
                rel.get("orgs")
                or rel.get("org")
                or rel.get("organization")
                or rel.get("organizations")
                or rel.get("rescues")
                or rel.get("rescue")
                or rel.get("shelter")
            )
            if isinstance(org_rel, dict):
                org_data = org_rel.get("data")
                if isinstance(org_data, list):
                    first = _first(org_data)
                    if isinstance(first, dict) and first.get("id"):
                        external_org_id = str(first["id"])
                elif isinstance(org_data, dict) and org_data.get("id"):
                    external_org_id = str(org_data["id"])

            # Build photos: relationship pictures -> included urls, plus thumb fallback
            photos: List[str] = []

            pics_rel = rel.get("pictures")
            if isinstance(pics_rel, dict):
                pics_data = pics_rel.get("data") or []
                if isinstance(pics_data, dict):
                    pics_data = [pics_data]
                if isinstance(pics_data, list):
                    collected: List[tuple[int, str]] = []
                    for ref in pics_data:
                        if not isinstance(ref, dict):
                            continue
                        pic_id = ref.get("id")
                        if not pic_id:
                            continue
                        meta = pic_meta_by_id.get(str(pic_id))
                        if meta:
                            collected.append(meta)

                    collected.sort(key=lambda t: t[0]) 
                    photos.extend([u for _, u in collected])

            # Fallback thumbnail if relationship didn't yield anything
            thumb = attrs.get("pictureThumbnailUrl")
            if thumb and not photos:
                photos.append(_upgrade_img_width(str(thumb), width=800))

            photos = _dedupe_keep_order(photos)

            # ...create ProviderPet as before, but now with photos list
            out.append(
                ProviderPet(
                    provider=self.provider_name,
                    external_pet_id=str(row.get("id")),
                    external_org_id=external_org_id,
                    name=str(attrs.get("name") or "").strip() or "Unknown",
                    species="DOG",
                    age_group=_map_age_group(attrs.get("ageGroup")),
                    size=_map_size(attrs.get("sizeGroup")),
                    sex=_map_sex(attrs.get("sex")),
                    breed_primary=attrs.get("breedPrimary"),
                    breed_secondary=attrs.get("breedSecondary"),
                    is_mixed=attrs.get("isBreedMixed"),
                    photos=photos,
                    raw_description=attrs.get("descriptionText") or "",
                    listed_at_iso=attrs.get("availableDate") or attrs.get("createdDate") or attrs.get("updatedDate"),
                    status="Available",
                    apply_url=(str(attrs.get("url")).strip() if attrs.get("url") else None),
                    apply_hint="Apply via RescueGroups" if attrs.get("url") else None,
                    raw=row,
                )
            )

        return out


def _map_age_group(v: Any) -> Optional[str]:
    # RescueGroups ageGroup Baby, Young Adult, Senior :contentReference[oaicite:5]{index=5}
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
    # RescueGroups sizeGroup Small, Medium, Large, X-Large :contentReference[oaicite:6]{index=6}
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
