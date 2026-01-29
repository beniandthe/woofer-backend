from typing import Optional, Tuple, List
from adoption.models import Pet
from adoption.services.ranking_service import RankingService
from adoption.services.ranked_cursor import decode_rank_cursor, encode_rank_cursor

DEFAULT_LIMIT = 20
MAX_LIMIT = 50
MAX_CANDIDATES = 500  # MVP guardrail


class PetFeedService:
    @staticmethod
    def get_feed(user, cursor: Optional[str], limit: Optional[int]) -> Tuple[List[Pet], Optional[str]]:
        lim = limit or DEFAULT_LIMIT
        lim = min(max(lim, 1), MAX_LIMIT)

        # Candidate set: stable deterministic DB fetch
        candidates = list(
            Pet.objects
            .select_related("organization")
            .filter(status=Pet.Status.ACTIVE)
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
