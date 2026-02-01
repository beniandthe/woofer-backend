from __future__ import annotations

import re
from datetime import timedelta
from typing import Optional, Tuple

from django.db import transaction
from django.utils import timezone

from adoption.models import Pet, RiskClassification


_MEDICAL_KEYWORDS = [
    "diabetes",
    "seizure",
    "blind",
    "deaf",
    "amput",
    "special needs",
    "medical",
    "needs medication",
    "wheelchair",
    "heartworm",
    "injury",
    "surgery",
]

# Very conservative, deterministic text scan
_MEDICAL_RE = re.compile("|".join(re.escape(k) for k in _MEDICAL_KEYWORDS), re.IGNORECASE)


class RiskBackfillService:
    """
    v0 deterministic risk classification heuristics.

    Goals:
    - Safe, idempotent updates.
    - Prefer false negatives over false positives (conservative).
    - No ML, no external calls.
    """

    # MVP defaults — tune later
    LONG_STAY_DAYS = 21

    @staticmethod
    def _is_long_stay(pet: Pet, now=None) -> bool:
        now = now or timezone.now()
        if not pet.listed_at:
            return False
        return (now - pet.listed_at) >= timedelta(days=RiskBackfillService.LONG_STAY_DAYS)

    @staticmethod
    def _is_senior(pet: Pet) -> bool:
        # Canon field exists: age_group = PUPPY | ADULT | SENIOR (nullable)
        return getattr(pet, "age_group", None) == "SENIOR"

    @staticmethod
    def _is_medical(pet: Pet) -> bool:
        raw = (pet.raw_description or "") + "\n" + (pet.ai_description or "")
        if not raw.strip():
            return False
        return bool(_MEDICAL_RE.search(raw))

    @staticmethod
    def classify(pet: Pet) -> dict:
        """
        Returns dict of RiskClassification boolean fields (excluding notes).
        """
        return {
            "is_long_stay": RiskBackfillService._is_long_stay(pet),
            "is_senior": RiskBackfillService._is_senior(pet),
            "is_medical": RiskBackfillService._is_medical(pet),
            # v0: keep false by default; later we can compute from breed group taxonomy
            "is_overlooked_breed_group": False,
            # v0: no returns data; default false
            "recently_returned": False,
        }

    @staticmethod
    @transaction.atomic
    def upsert_for_pet(pet: Pet) -> Tuple[RiskClassification, bool]:
        flags = RiskBackfillService.classify(pet)
        obj, created = RiskClassification.objects.update_or_create(
            pet=pet,
            defaults=flags,
        )
        return obj, created

    @staticmethod
    def backfill_queryset(qs) -> int:
        """
        Backfill risk classification for a queryset of pets.
        Returns count processed.
        """
        count = 0
        for pet in qs.iterator():
            RiskBackfillService.upsert_for_pet(pet)
            count += 1
        return count

    @staticmethod
    def backfill_all_active() -> int:
        qs = Pet.objects.filter(status=Pet.Status.ACTIVE)
        return RiskBackfillService.backfill_queryset(qs)
