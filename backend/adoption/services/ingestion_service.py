from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple, List
from django.db import transaction
from django.utils import timezone
from adoption.services.pet_enrichment_service import PetEnrichmentService
from adoption.services.zip_geo_service import ZipGeoService
from adoption.models import Organization, Pet
from typing import Set

@dataclass(frozen=True)
class IngestResult:
    organizations_created: int
    organizations_updated: int
    pets_created: int
    pets_updated: int
    pets_skipped: int

    pets_seen_external_ids: Set[str]
    
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

        postal_code = (org.get("postal_code", "") or "").strip()

        # 1) Fetch existing first (so we can decide whether geo is allowed to change)
        existing = (
            Organization.objects
            .filter(source=source, source_org_id=source_org_id)
            .only("organization_id", "geo_source", "latitude", "longitude", "postal_code")
            .first()
        )

        existing_geo_source = (existing.geo_source or "") if existing else ""
        has_existing_geo = bool(existing and existing.latitude is not None and existing.longitude is not None)

        # 2) Base defaults (non-geo fields always safe to update)
        defaults: Dict[str, Any] = {
            "name": org.get("name") or (source_org_id or "Unknown Organization"),
            "contact_email": org.get("contact_email"),
            "location": org.get("location") or "Unknown",
            "postal_code": postal_code,
            "is_active": bool(org.get("is_active", True)),
        }

        # 3) Geo policy:
        # - If existing geo_source is non-empty and not ZIP, do NOT overwrite.
        # - Else, we may set/refresh ZIP geo if we have a match.
        allow_zip_geo = (existing is None) or (existing_geo_source in ("", "ZIP"))

        if allow_zip_geo and postal_code:
            z = ZipGeoService.normalize_zip(postal_code)
            if z:
                hit = ZipGeoService.lookup(z)
                if hit:
                    defaults.update(
                        {
                            "latitude": hit.lat,
                            "longitude": hit.lon,
                            "geo_source": "ZIP",
                            "geo_updated_at": timezone.now(),
                        }
                    )
                else:
                    # If we have no geo and no match, leave geo fields untouched.
                    # (Do NOT null them out.)
                    pass

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

        incoming_listed_at = pet.get("listed_at")

        # Preserve listed_at once set (fairness long-stay must not reset on re-sync)
        existing = (
            Pet.objects.filter(source=source, external_id=str(external_id))
            .only("listed_at")
            .first()
        )
        if existing and existing.listed_at:
            listed_at = existing.listed_at
        else:
            listed_at = incoming_listed_at or timezone.now()

        # Descriptions (raw + AI) 
        raw_desc = pet.get("raw_description") or ""
        ai_desc = pet.get("ai_description")
        raw_photos = pet.get("photos") or []
        photos = [u.strip() for u in raw_photos if isinstance(u, str) and u.strip()]

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
            "photos": photos,
            "raw_description": raw_desc,
            "listed_at": listed_at,
            "status": pet.get("status") or "ACTIVE",
            "apply_url": pet.get("apply_url", "") or "",
            "apply_hint": pet.get("apply_hint", "") or "",
        }

        # If upstream provides ai_description, keep it, otherwise generate from raw_description
        if ai_desc:
            defaults["ai_description"] = ai_desc
        else:
            generated = PetEnrichmentService.generate_fun_neutral_summary(raw_desc)
            if generated:
                defaults["ai_description"] = generated

        obj, created = Pet.objects.update_or_create(
            source=source,
            external_id=str(external_id),
            defaults=defaults,
        )
        return obj, created, False

    @staticmethod
    @transaction.atomic
    def ingest_canonical(org_dicts: Iterable[Dict[str, Any]],pet_dicts: Iterable[Dict[str, Any]],
) -> IngestResult:
        org_created = org_updated = 0
        pet_created = pet_updated = pet_skipped = 0

        pets_seen: Set[str] = set()
        touched_pets: List["Pet"] = []  # pets created/updated this run (non skipped)

        for org in org_dicts:
            o, created = IngestionService.upsert_organization(org)
            if created:
                org_created += 1
            else:
                org_updated += 1

        for pet in pet_dicts:
            external_id = pet.get("external_id")
            if external_id:
                pets_seen.add(str(external_id))

            p, created, skipped = IngestionService.upsert_pet(pet)
            if skipped:
                pet_skipped += 1
                continue

            touched_pets.append(p)

            if created:
                pet_created += 1
            else:
                pet_updated += 1

        # Enrich only pets touched in this ingestion run
        # Non blocking behavior is handled inside PetEnrichmentService
        PetEnrichmentService.enrich_missing_ai_descriptions(touched_pets)

        return IngestResult(
            organizations_created=org_created,
            organizations_updated=org_updated,
            pets_created=pet_created,
            pets_updated=pet_updated,
            pets_skipped=pet_skipped,
            pets_seen_external_ids=pets_seen,
        )
   


