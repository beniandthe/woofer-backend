from typing import Optional, Tuple, List
import math
from adoption.models import Pet, AdopterProfile, Interest, PetSeen, Application
from adoption.services.ranking_service import RankingService, DIVERSITY_TARGET_BOOSTED_RATIO, DIVERSITY_MIN_NORMAL_PER_PAGE
from adoption.services.ranked_cursor import decode_rank_cursor, encode_rank_cursor
from django.db.models import Subquery
from adoption.services.user_profile_service import UserProfileService

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_CANDIDATES = 500  # MVP


class PetFeedService:
    @staticmethod
    def get_feed(user, cursor: Optional[str], limit: Optional[int]) -> Tuple[List[Pet], Optional[str]]:
        lim = limit or DEFAULT_LIMIT
        lim = min(max(lim, 1), MAX_LIMIT)
        profile = UserProfileService.get_or_create_profile(user)


        # Candidate set: stable DB fetch
        base_qs = (
            Pet.objects
            .select_related("organization")
            .filter(status=Pet.Status.ACTIVE)
        )

        #apply server side profile filters BEFORE ranking/pagination
        base_qs = PetFeedService._apply_profile_filters(base_qs, profile)

        # Exclude "already decided" pets (user scoped)
        if user is not None and getattr(user, "is_authenticated", False):
            
            # liked/interest
            liked_pet_ids = Interest.objects.filter(user=user).values("pet_id")

            # applied
            applied_pet_ids = Application.objects.filter(user=user).values("pet_id") 

            # passed/seen
            # If PetSeen == "seen means passed", then just filter by user
            passed_pet_ids = PetSeen.objects.filter(user=user).values("pet_id")

            base_qs = (
                base_qs
                .exclude(pet_id__in=Subquery(liked_pet_ids))
                .exclude(pet_id__in=Subquery(applied_pet_ids))
                .exclude(pet_id__in=Subquery(passed_pet_ids))
            )

        candidates = list(
            base_qs
            .order_by("-listed_at", "-pet_id")[:MAX_CANDIDATES]
        )

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
        prefs = profile.preferences or {}

        preferred_sizes = prefs.get("preferred_sizes") or []
        if preferred_sizes:
            qs = qs.filter(size__in=preferred_sizes)

        preferred_age_groups = prefs.get("preferred_age_groups") or []
        if preferred_age_groups:
            qs = qs.filter(age_group__in=preferred_age_groups)

        home_zip = (profile.home_postal_code or "").strip()
        max_distance = (profile.preferences or {}).get("max_distance_miles")

        if home_zip and max_distance:
            try:
                md = int(max_distance)
            except (TypeError, ValueError):
                md = None

            if md is not None:
                if md <= 10:
                    # Very local exact ZIP
                    qs = qs.filter(organization__postal_code=home_zip)
                elif md <= 100:
                    # Regional ZIP prefix 
                    prefix = home_zip[:3]
                    if prefix:
                        qs = qs.filter(organization__postal_code__startswith=prefix)
                else:
                    # >100: MVP does not apply zip filtering (no geocoding yet)
                    pass

        # Lean MVP hard constraints
        # treat each hard constraint as "required temperament tag"
        hard_constraints = prefs.get("hard_constraints") or []
        for c in hard_constraints:
            if isinstance(c, str) and c.strip():
                qs = qs.filter(temperament_tags__contains=[c.strip()])

        return qs

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

    
