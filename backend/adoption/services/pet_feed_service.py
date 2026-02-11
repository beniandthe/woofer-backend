from typing import Optional, Tuple, List
from adoption.models import Pet
from adoption.services.ranking_service import RankingService
from adoption.services.ranked_cursor import decode_rank_cursor, encode_rank_cursor
from adoption.services.user_profile_service import UserProfileService
from adoption.models import AdopterProfile

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_CANDIDATES = 500  # MVP guardrail


class PetFeedService:
    @staticmethod
    def get_feed(user, cursor: Optional[str], limit: Optional[int]) -> Tuple[List[Pet], Optional[str]]:
        lim = limit or DEFAULT_LIMIT
        lim = min(max(lim, 1), MAX_LIMIT)
        profile = UserProfileService.get_or_create_profile(user)


        # Candidate set: stable deterministic DB fetch
        base_qs = (
            Pet.objects
            .select_related("organization")
            .filter(status=Pet.Status.ACTIVE)
        )

        #apply server-side profile filters BEFORE ranking/pagination
        base_qs = PetFeedService._apply_profile_filters(base_qs, profile)

        candidates = list(
            base_qs
            .order_by("-listed_at", "-pet_id")[:MAX_CANDIDATES]
        )

        ranked = RankingService.rank(candidates)  # score DESC, pet_id DESC

        if cursor:
            last_score, last_pet_id = decode_rank_cursor(cursor)
            ranked = [
                rp for rp in ranked
                if (rp.score < last_score) or (rp.score == last_score and str(rp.pet.pet_id) < last_pet_id)
            ]

        page = ranked[:lim]
        pets = [rp.pet for rp in page]

        if len(page) < lim:
            return pets, None

        last = page[-1]
        next_cursor = encode_rank_cursor(last.score, str(last.pet.pet_id))
        return pets, next_cursor


    @staticmethod
    def _apply_profile_filters(qs, profile: AdopterProfile):
        prefs = profile.preferences or {}

        preferred_sizes = prefs.get("preferred_sizes") or []
        if preferred_sizes:
            qs = qs.filter(size__in=preferred_sizes)

        preferred_age_groups = prefs.get("preferred_age_groups") or []
        if preferred_age_groups:
            qs = qs.filter(age_group__in=preferred_age_groups)

        # Lean MVP hard constraints:
        # treat each hard constraint as "required temperament tag"
        hard_constraints = prefs.get("hard_constraints") or []
        for c in hard_constraints:
            if isinstance(c, str) and c.strip():
                qs = qs.filter(temperament_tags__contains=[c.strip()])

        return qs

    
