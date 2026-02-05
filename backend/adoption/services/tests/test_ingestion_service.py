from django.test import TestCase
from django.utils import timezone

from adoption.models import Organization, Pet
from adoption.services.ingestion_service import IngestionService


class IngestionServiceTests(TestCase):
    def test_ingest_canonical_is_idempotent(self):
        org_dicts = [
            {
                "source": "RESCUEGROUPS",
                "source_org_id": "RG123",
                "name": "Test Org",
                "contact_email": "org@example.com",
                "location": "Los Angeles, CA",
                "is_active": True,
            }
        ]

        pet_dicts = [
            {
                "source": "RESCUEGROUPS",
                "external_id": "P1",
                "organization_source_org_id": "RG123",
                "name": "Bella",
                "species": "DOG",
                "photos": ["https://example.com/a.jpg"],
                "raw_description": "Sweet dog",
                "listed_at": timezone.now(),
                "status": "ACTIVE",
            }
        ]

        r1 = IngestionService.ingest_canonical(org_dicts, pet_dicts)
        self.assertEqual(r1.organizations_created, 1)
        self.assertEqual(r1.pets_created, 1)

        r2 = IngestionService.ingest_canonical(org_dicts, pet_dicts)
        self.assertEqual(r2.organizations_created, 0)
        self.assertEqual(r2.organizations_updated, 1)
        self.assertEqual(r2.pets_created, 0)
        self.assertEqual(r2.pets_updated, 1)

        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Pet.objects.count(), 1)

    def test_skips_pet_missing_org_link(self):
        org_dicts = [
            {"source": "RESCUEGROUPS", "source_org_id": "RG123", "name": "Org", "location": "LA, CA", "is_active": True}
        ]
        pet_dicts = [
            {"source": "RESCUEGROUPS", "external_id": "P2", "name": "NoOrg", "species": "DOG"}
        ]

        r = IngestionService.ingest_canonical(org_dicts, pet_dicts)
        self.assertEqual(r.pets_created, 0)
        self.assertEqual(r.pets_skipped, 1)
        self.assertEqual(Pet.objects.count(), 0)
