from typing import Optional, Tuple, List
from django.db.models import Q
from adoption.models import Pet
from adoption.services.cursor import decode_cursor, encode_cursor

DEFAULT_LIMIT = 20
MAX_LIMIT = 50

class PetFeedService:
    @staticmethod
    def get_feed(user, cursor: Optional[str], limit: Optional[int]) -> Tuple[List[Pet], Optional[str]]:
        lim = limit or DEFAULT_LIMIT
        lim = min(max(lim, 1), MAX_LIMIT)

        qs = (
            Pet.objects
            .select_related("organization")
            .filter(status=Pet.Status.ACTIVE)
            .order_by("-listed_at", "-pet_id")
        )

        if cursor:
            last_listed_at, last_pet_id = decode_cursor(cursor)

            # Sorting is DESC. "Next page" means records strictly after the cursor in this ordering.
            # (listed_at < last_listed_at) OR (listed_at == last_listed_at AND pet_id < last_pet_id)
            if last_listed_at is None:
                qs = qs.filter(pet_id__lt=last_pet_id)
            else:
                qs = qs.filter(
                    Q(listed_at__lt=last_listed_at) |
                    (Q(listed_at=last_listed_at) & Q(pet_id__lt=last_pet_id))
                )

        items = list(qs[:lim])

        if len(items) < lim:
            return items, None

        last = items[-1]
        next_cursor = encode_cursor(last.listed_at, str(last.pet_id))
        return items, next_cursor
