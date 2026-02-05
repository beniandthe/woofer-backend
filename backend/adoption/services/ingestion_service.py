from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from adoption.models import Organization, Pet


@dataclass(frozen=True)
class IngestResult:
    organizations_created: int
    organizations_updated: int
    pets_created: int
    pets_updated: int
    pets_skipped: int


class IngestionService:
    """
    Provider-neutral DB ingestion:
    consumes canonical dicts produced by provider mappers.
    """

    @staticmethod
    def upsert_organization(org: Dict[str, Any]) -> Tuple[Organization, bool]:
        # Required keys
        source = org.get("source")
        source_org_id = org.get("source_org_id")
        if not source or not source_org_id:
            raise ValueError("Organization missing required keys: source, source_org_id")

        defaults = {
            "name": org.get("name") or (source_org_id or "Unknown Organization"),
            "contact_email": org.get("contact_email"),
            "location": org.get("location") or "Unknown",
            "is_active": bool(org.get("is_active", True)),
        }

        obj, created = Organization.objects.update_or_create(
            source=source,
            source_org_id=source_org_id,
            defaults=defaults,
        )
        return obj, created

    @staticmethod
    def upsert_pet(pet: Dict[str, Any]) -> Tuple[Optional[Pet], bool, bool]:
        """
        Returns: (pet_or_none, created?, skipped?)
        Skipped when required keys or org link is missing.
        """
        source = pet.get("source")
        external_id = pet.get("external_id")
        org_source_org_id = pet.get("organization_source_org_id")

        if not source or not external_id:
            return None, False, True
        if not org_source_org_id:
            return None, False, True

        try:
            org = Organization.objects.get(source=source, source_org_id=org_source_org_id)
        except Organization.DoesNotExist:
            return None, False, True

        defaults = {
            "organization": org,
            "name": pet.get("name") or "Unknown",
            "species": pet.get("species") or "DOG",
            "age_group": pet.get("age_group"),
            "size": pet.get("size"),
            "sex": pet.get("sex"),
            "breed_primary": pet.get("breed_primary"),
            "breed_secondary": pet.get("breed_secondary"),
            "is_mixed": bool(pet.get("is_mixed", False)),
            "photos": pet.get("photos") or [],
            "raw_description": pet.get("raw_description") or "",
            "listed_at": pet.get("listed_at") or timezone.now(),
            "status": pet.get("status") or "ACTIVE",
        }

        obj, created = Pet.objects.update_or_create(
            source=source,
            external_id=str(external_id),
            defaults=defaults,
        )
        return obj, created, False

    @staticmethod
    @transaction.atomic
    def ingest_canonical(
        org_dicts: Iterable[Dict[str, Any]],
        pet_dicts: Iterable[Dict[str, Any]],
    ) -> IngestResult:
        org_created = org_updated = 0
        pet_created = pet_updated = pet_skipped = 0

        for org in org_dicts:
            o, created = IngestionService.upsert_organization(org)
            if created:
                org_created += 1
            else:
                org_updated += 1

        for pet in pet_dicts:
            p, created, skipped = IngestionService.upsert_pet(pet)
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
