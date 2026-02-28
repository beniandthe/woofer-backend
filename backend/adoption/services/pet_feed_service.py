from typing import Optional, Tuple, List
import math
from decimal import Decimal
from adoption.models import Pet, AdopterProfile, Interest, PetSeen, Application
from adoption.services.ranking_service import RankingService, DIVERSITY_TARGET_BOOSTED_RATIO, DIVERSITY_MIN_NORMAL_PER_PAGE
from adoption.services.ranked_cursor import decode_rank_cursor, encode_rank_cursor
from django.db.models import Subquery
from adoption.services.user_profile_service import UserProfileService
from adoption.services.zip_geo_service import ZipGeoService

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_CANDIDATES = 500  # MVP


class PetFeedService:
    @staticmethod
    def get_feed(user, cursor: Optional[str], limit: Optional[int]) -> Tuple[List[Pet], Optional[str]]:
        lim = limit or DEFAULT_LIMIT
        lim = min(max(lim, 1), MAX_LIMIT)
        profile = UserProfileService.get_or_create_profile(user)

        base_qs = (
            Pet.objects
            .select_related("organization")
            .filter(status=Pet.Status.ACTIVE)
        )

        # APPLY PROFILE FILTERS (returns distance_ctx)
        base_qs, distance_ctx = PetFeedService._apply_profile_filters(base_qs, profile)

        # Exclude "already decided" pets (user scoped)
        if user is not None and getattr(user, "is_authenticated", False):
            liked_pet_ids = Interest.objects.filter(user=user).values("pet_id")
            applied_pet_ids = Application.objects.filter(user=user).values("pet_id")
            passed_pet_ids = PetSeen.objects.filter(user=user).values("pet_id")

            base_qs = (
                base_qs
                .exclude(pet_id__in=Subquery(liked_pet_ids))
                .exclude(pet_id__in=Subquery(applied_pet_ids))
                .exclude(pet_id__in=Subquery(passed_pet_ids))
            )

        # Candidate set: stable deterministic DB fetch
        candidates = list(
            base_qs
            .order_by("-listed_at", "-pet_id")[:MAX_CANDIDATES]
        )

        # PRECISE DISTANCE FILTER (after DB filter/candidate cap)
        if distance_ctx is not None:
            center_lat, center_lon = distance_ctx["center"]
            max_miles = distance_ctx["miles"]

            candidates = [
                p for p in candidates
                if PetFeedService._within_radius_miles(
                    center_lat, center_lon,
                    getattr(p.organization, "latitude", None),
                    getattr(p.organization, "longitude", None),
                    max_miles,
                )
            ]

        ranked = RankingService.rank(candidates, profile=profile)
        ranked = PetFeedService._apply_diversity_slotting(ranked)

        if cursor:
            last_score, last_pet_id = decode_rank_cursor(cursor)
            ranked = [
                rp for rp in ranked
                if (rp.score < last_score) or (rp.score == last_score and str(rp.pet.pet_id) < last_pet_id)
            ]

        page = PetFeedService._select_page_with_diversity(ranked, lim)
        pets = [rp.pet for rp in page]

        if len(page) < lim:
            return pets, None

        last = page[-1]
        next_cursor = encode_rank_cursor(last.score, str(last.pet.pet_id))
        return pets, next_cursor

    @staticmethod
    def _apply_diversity_slotting(ranked):
        """
        Deterministically mix boosted and non-boosted pets.
        Keeps ordering stable within each group.
        Guarantees termination.
        """
        boosted = []
        normal = []

        for rp in ranked:
            if RankingService.is_boosted(rp.reasons):
                boosted.append(rp)
            else:
                normal.append(rp)

        if not boosted or not normal:
            return ranked

        total = len(ranked)

        # target boosted count within the first total items
        target_boosted = int(total * DIVERSITY_TARGET_BOOSTED_RATIO)
        target_boosted = max(1, min(target_boosted, len(boosted)))

        mixed = []
        b_i = 0
        n_i = 0
        boosted_used = 0

        # Hard guarantee: at most 'total' appends
        while len(mixed) < total:
            # Prefer boosted until we hit the target, BUT if normal is exhausted,
            # we must keep consuming boosted so we terminate
            if b_i < len(boosted) and (boosted_used < target_boosted or n_i >= len(normal)):
                mixed.append(boosted[b_i])
                b_i += 1
                boosted_used += 1
                continue

            if n_i < len(normal):
                mixed.append(normal[n_i])
                n_i += 1
                continue

            # If we get here, normal is exhausted, consume remaining boosted
            if b_i < len(boosted):
                mixed.append(boosted[b_i])
                b_i += 1
                continue

            # Nothing left 
            break

        return mixed

    @staticmethod
    def _apply_profile_filters(qs, profile: AdopterProfile):
        """
        Returns: (qs, distance_ctx)
        distance_ctx is either None or {"center": (lat, lon), "miles": md}

        12.5.4 rule:
        If home_postal_code and max_distance_miles are present and valid:
          - require org lat/lon (exclude missing)
          - filter via haversine in python (after candidate fetch)
        """
        prefs = profile.preferences or {}

        preferred_sizes = prefs.get("preferred_sizes") or []
        if preferred_sizes:
            qs = qs.filter(size__in=preferred_sizes)

        preferred_age_groups = prefs.get("preferred_age_groups") or []
        if preferred_age_groups:
            qs = qs.filter(age_group__in=preferred_age_groups)

        distance_ctx = None

        home_zip_raw = (profile.home_postal_code or "").strip()
        home_zip = ZipGeoService.normalize_zip(home_zip_raw)
        max_distance = (prefs or {}).get("max_distance_miles")

        md: Optional[int] = None
        if max_distance is not None:
            try:
                md = int(max_distance)
            except (TypeError, ValueError):
                md = None

        if home_zip and md is not None and md > 0:
            # Resolve home centroid (offline)
            home = ZipGeoService.lookup(home_zip)
            latlon = PetFeedService._extract_lat_lon(home)

            if latlon is not None:
                center_lat, center_lon = latlon
                distance_ctx = {"center": (center_lat, center_lon), "miles": md}

                # Exclude orgs that cannot be distance filtered
                qs = qs.exclude(organization__latitude__isnull=True).exclude(organization__longitude__isnull=True)

                # Optional: DB-side bounding box to reduce candidates BEFORE Python haversine
                lat_delta, lon_delta = PetFeedService._bbox_deltas_miles(center_lat, md)
                lat_min = Decimal(str(center_lat - lat_delta))
                lat_max = Decimal(str(center_lat + lat_delta))
                lon_min = Decimal(str(center_lon - lon_delta))
                lon_max = Decimal(str(center_lon + lon_delta))

                qs = qs.filter(
                    organization__latitude__gte=lat_min,
                    organization__latitude__lte=lat_max,
                    organization__longitude__gte=lon_min,
                    organization__longitude__lte=lon_max,
                )

        # Lean MVP hard constraints
        hard_constraints = prefs.get("hard_constraints") or []
        for c in hard_constraints:
            if isinstance(c, str) and c.strip():
                qs = qs.filter(temperament_tags__contains=[c.strip()])

        return qs, distance_ctx

    @staticmethod
    def _select_page_with_diversity(ranked, lim: int):
        """
        Cursor-safe diversity:
        - ranked is already globally sorted (score desc, pet_id desc)
        - we SELECT a page without reordering the list
        - enforce boosted cap + at least some normal when available
        """
        if lim <= 0:
            return []

        # Pre-scan counts to decide if we can enforce normal presence
        boosted_total = 0
        normal_total = 0
        for rp in ranked:
            if RankingService.is_boosted(rp.reasons):
                boosted_total += 1
            else:
                normal_total += 1

        # If only one type exists, just take the first page
        if boosted_total == 0 or normal_total == 0:
            return ranked[:lim]

        # Max boosted allowed in the page
        max_boosted = int(math.ceil(lim * DIVERSITY_TARGET_BOOSTED_RATIO))
        max_boosted = max(1, min(max_boosted, boosted_total))

        # Enforce at least one normal if possible
        min_normal = min(DIVERSITY_MIN_NORMAL_PER_PAGE, normal_total)
        # Therefore max boosted can't consume the whole page
        max_boosted = min(max_boosted, lim - min_normal)

        selected = []
        boosted_used = 0
        normal_used = 0

        # First pass fill respecting max_boosted
        for rp in ranked:
            if len(selected) >= lim:
                break

            is_boosted = RankingService.is_boosted(rp.reasons)

            if is_boosted:
                if boosted_used >= max_boosted:
                    continue
                boosted_used += 1
                selected.append(rp)
            else:
                normal_used += 1
                selected.append(rp)

        # If we didn't fill the page because we skipped too many boosted,
        # fill remaining slots with whatever is next in ranked order
        if len(selected) < lim:
            chosen_ids = {str(rp.pet.pet_id) for rp in selected}
            for rp in ranked:
                if len(selected) >= lim:
                    break
                if str(rp.pet.pet_id) in chosen_ids:
                    continue
                selected.append(rp)

        return selected

    @staticmethod
    def _extract_lat_lon(obj):
        """
        ZipGeoService.lookup() may return a dict, tuple, or object.
        Normalize to (float_lat, float_lon) or None.
        """
        if obj is None:
            return None

        lat = lon = None
        if isinstance(obj, dict):
            lat = obj.get("lat") or obj.get("latitude")
            lon = obj.get("lon") or obj.get("longitude")
        elif isinstance(obj, (tuple, list)) and len(obj) >= 2:
            lat, lon = obj[0], obj[1]
        else:
            lat = getattr(obj, "lat", None) or getattr(obj, "latitude", None)
            lon = getattr(obj, "lon", None) or getattr(obj, "longitude", None)

        if lat is None or lon is None:
            return None

        try:
            return float(lat), float(lon)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _bbox_deltas_miles(center_lat: float, miles: int):
        """
        Approx degrees per mile bounding box.
        """
        # 1 deg lat ~ 69 miles
        lat_delta = float(miles) / 69.0
        # 1 deg lon ~ 69*cos(lat) miles
        denom = 69.0 * max(0.1, math.cos(math.radians(center_lat)))
        lon_delta = float(miles) / denom
        return lat_delta, lon_delta

    @staticmethod
    def _within_radius_miles(center_lat, center_lon, org_lat, org_lon, max_miles: int) -> bool:
        if org_lat is None or org_lon is None:
            return False

        try:
            lat2 = float(org_lat)
            lon2 = float(org_lon)
        except (TypeError, ValueError):
            return False

        # Haversine (miles)
        r_miles = 3958.7613
        dlat = math.radians(lat2 - center_lat)
        dlon = math.radians(lon2 - center_lon)

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(math.radians(center_lat)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return (r_miles * c) <= float(max_miles)
