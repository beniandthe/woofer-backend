from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from adoption.models import Organization, Pet

from adoption.services.petfinder_mapper import (
    map_petfinder_org_to_canonical,
    map_petfinder_pet_to_canonical,
    SOURCE_PETFINDER,
)


@dataclass(frozen=True)
class IngestResult:
    organizations_created: int
    organizations_updated: int
    pets_created: int
    pets_updated: int
    pets_skipped: int


class IngestionService:
    """
    DB-writing ingestion boundary: external dicts -> canonical models.
    Petfinder-specific mapping lives in petfinder_mapper.
    """

    @staticmethod
    def upsert_organization_from_petfinder(org_payload: Dict[str, Any]) -> Tuple[Organization, bool]:
        data = map_petfinder_org_to_canonical(org_payload)

        # Idempotent key
        source = data["source"]
        source_org_id = data["source_org_id"]
        if not source_org_id:
            # Extremely defensive: cannot upsert without a stable external key
            raise ValueError("Petfinder org missing id/source_org_id")

        obj, created = Organization.objects.update_or_create(
            source=source,
            source_org_id=source_org_id,
            defaults={
                "name": data["name"],
                "contact_email": data.get("contact_email"),
                "location": data.get("location") or "Unknown",
                "is_active": True,
            },
        )
        return obj, created

    @staticmethod
    def upsert_pet_from_petfinder(animal_payload: Dict[str, Any]) -> Tuple[Optional[Pet], bool, bool]:
        """
        Returns: (pet or None, created?, skipped?)
        skipped means not ingested due to missing required keys.
        """
        data = map_petfinder_pet_to_canonical(animal_payload)

        if not data.get("external_id"):
            return None, False, True

        org_source_org_id = data.get("organization_source_org_id")
        if not org_source_org_id:
            # If we can't link to an org, skip for now (lean MVP)
            return None, False, True

        try:
            org = Organization.objects.get(source=SOURCE_PETFINDER, source_org_id=org_source_org_id)
        except Organization.DoesNotExist:
            # If org wasn’t ingested yet, skip (caller can choose to ingest orgs first)
            return None, False, True

        defaults = {
            "organization": org,
            "name": data["name"],
            "species": data["species"],
            "photos": data.get("photos", []),
            "raw_description": data.get("raw_description", ""),
            # Keep ai_description untouched here; enrichment is later sprint
            "listed_at": data.get("listed_at") or timezone.now(),
            "status": data.get("status", "ACTIVE"),
        }

        pet, created = Pet.objects.update_or_create(
            source=data["source"],
            external_id=data["external_id"],
            defaults=defaults,
        )

        return pet, created, False

    @staticmethod
    @transaction.atomic
    def ingest_petfinder(orgs: Iterable[Dict[str, Any]], animals: Iterable[Dict[str, Any]]) -> IngestResult:
        org_created = org_updated = 0
        pet_created = pet_updated = pet_skipped = 0

        # 1) Orgs first
        for org_payload in orgs:
            org, created = IngestionService.upsert_organization_from_petfinder(org_payload)
            if created:
                org_created += 1
            else:
                org_updated += 1

        # 2) Pets next
        for animal_payload in animals:
            pet, created, skipped = IngestionService.upsert_pet_from_petfinder(animal_payload)
            if skipped:
                pet_skipped += 1
                continue
            if created:
                pet_created += 1
            else:
                pet_updated += 1

        return IngestResult(
            organizations_created=org_created,
            organizations_updated=org_updated,
            pets_created=pet_created,
            pets_updated=pet_updated,
            pets_skipped=pet_skipped,
        )
