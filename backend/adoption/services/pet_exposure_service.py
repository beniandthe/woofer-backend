from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from adoption.models import Pet, PetExposureStats


@dataclass(frozen=True)
class ExposureBumpResult:
    stats_id: int
    created: bool


class PetExposureService:
    """
    Sprint 12.1 scope:
      - Create/get stats row deterministically (unique per user+pet)
      - Provide atomic bump helpers

    IMPORTANT (idempotency):
      - Later stories (12.3) must call bump_like/apply/pass ONLY when the
        underlying Interest/Application/PetSeen row was newly created.
      - This service does not decide idempotency; it only increments safely.
    """

    @staticmethod
    @transaction.atomic
    def get_or_create(user, pet: Pet) -> tuple[PetExposureStats, bool]:
        return PetExposureStats.objects.get_or_create(
            user=user,
            pet=pet,
            defaults={},
        )

    @staticmethod
    @transaction.atomic
    def bump_impression(user, pet: Pet, at: Optional[timezone.datetime] = None) -> ExposureBumpResult:
        stats, created = PetExposureStats.objects.get_or_create(user=user, pet=pet)
        ts = at or timezone.now()

        PetExposureStats.objects.filter(pk=stats.pk).update(
            impressions_count=F("impressions_count") + 1,
            last_impression_at=ts,
        )
        return ExposureBumpResult(stats_id=stats.pk, created=created)

    @staticmethod
    @transaction.atomic
    def bump_like(user, pet: Pet) -> ExposureBumpResult:
        stats, created = PetExposureStats.objects.get_or_create(user=user, pet=pet)
        PetExposureStats.objects.filter(pk=stats.pk).update(
            likes_count=F("likes_count") + 1,
        )
        return ExposureBumpResult(stats_id=stats.pk, created=created)

    @staticmethod
    @transaction.atomic
    def bump_apply(user, pet: Pet) -> ExposureBumpResult:
        stats, created = PetExposureStats.objects.get_or_create(user=user, pet=pet)
        PetExposureStats.objects.filter(pk=stats.pk).update(
            applies_count=F("applies_count") + 1,
        )
        return ExposureBumpResult(stats_id=stats.pk, created=created)

    @staticmethod
    @transaction.atomic
    def bump_pass(user, pet: Pet) -> ExposureBumpResult:
        stats, created = PetExposureStats.objects.get_or_create(user=user, pet=pet)
        PetExposureStats.objects.filter(pk=stats.pk).update(
            passes_count=F("passes_count") + 1,
        )
        return ExposureBumpResult(stats_id=stats.pk, created=created)