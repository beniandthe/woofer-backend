import json
from django.test import TestCase
from django.utils import timezone

from adoption.models import Pet
from adoption.services.ingestion_service import IngestionService
from adoption.services.pet_enrichment_service import PetEnrichmentService


class IngestionEnrichmentTests(TestCase):
    def test_ingest_enriches_ai_description_when_missing(self):
        now = timezone.now()

        org_dicts = [
            {
                "source": "RESCUEGROUPS",
                "source_org_id": "RG123",
                "name": "Test Org",
                "contact_email": "org@example.com",
                "location": "Los Angeles, CA",
                "is_active": True,
                "postal_code": "90012",
            }
        ]

        raw_desc = "Sweet, gentle dog who loves people and enjoys calm walks. Good with kids."
        expected = PetEnrichmentService.generate_fun_neutral_summary(raw_desc)
        self.assertTrue(expected)  # sanity: generator must return something

        pet_dicts = [
            {
                "source": "RESCUEGROUPS",
                "external_id": "P1",
                # IMPORTANT: this key must match what your upsert_pet expects to link orgs.
                # If your upsert_pet uses a different key name, change it here to match.
                "organization_source_org_id": "RG123",

                "name": "Bella",
                "species": "DOG",
                "age_group": "ADULT",
                "size": "M",
                "sex": "FEMALE",

                "photos": ["https://example.com/a.jpg"],
                "raw_description": raw_desc,

                # intentionally missing
                "ai_description": None,

                "temperament_tags": [],
                "listed_at": now,
                "last_seen_at": now,
                "status": "ACTIVE",
            }
        ]

        result = IngestionService.ingest_canonical(org_dicts, pet_dicts)
        self.assertEqual(result.pets_created, 1)
        self.assertEqual(result.pets_skipped, 0)

        pet = Pet.objects.get(source="RESCUEGROUPS", external_id="P1")
        self.assertIsNotNone(pet.ai_description)
        self.assertNotEqual(pet.ai_description.strip(), "")
        self.assertEqual(pet.ai_description, expected)
