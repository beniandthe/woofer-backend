from __future__ import annotations

from typing import Iterable, List, Optional

from django.db import transaction
from django.utils import timezone

from adoption.models import Pet, PetImpression
from adoption.services.pet_exposure_service import PetExposureService


class PetImpressionService:
    @staticmethod
    @transaction.atomic
    def record_feed_impressions(
        *,
        user,
        pets: Iterable[Pet],
        cursor: Optional[str],
        limit: int,
    ) -> List[str]:
        """
        Deterministic + idempotent impression recording.

        Impression key = (user, pet, page_cursor_key, page_limit)

        - page_cursor_key = cursor or ""
        - page_limit = effective limit used by feed normalization
        """
        cursor_key = cursor or ""
        ts = timezone.now()

        created_pet_ids: List[str] = []
        for pet in pets:
            _, created = PetImpression.objects.get_or_create(
                user=user,
                pet=pet,
                page_cursor_key=cursor_key,
                page_limit=limit,
            )
            if created:
                PetExposureService.bump_impression(user, pet, at=ts)
                created_pet_ids.append(str(pet.pet_id))

        return created_pet_ids