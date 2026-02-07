from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
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

class IngestionListedAtTests(TestCase):
    def test_listed_at_set_on_first_ingest(self):
        org_dicts = [{
            "source": "RESCUEGROUPS",
            "source_org_id": "RG123",
            "name": "Org",
            "contact_email": "org@example.com",
            "location": "LA, CA",
            "is_active": True,
        }]

        first_time = timezone.now() - timedelta(days=30)
        pet_dicts = [{
            "source": "RESCUEGROUPS",
            "external_id": "P1",
            "organization_source_org_id": "RG123",
            "name": "Bella",
            "species": "DOG",
            "photos": [],
            "raw_description": "",
            "listed_at": first_time,
            "status": "ACTIVE",
        }]

        IngestionService.ingest_canonical(org_dicts, pet_dicts)
        p = Pet.objects.get(source="RESCUEGROUPS", external_id="P1")
        self.assertEqual(p.listed_at, first_time)

    def test_listed_at_not_overwritten_on_resync(self):
        org_dicts = [{
            "source": "RESCUEGROUPS",
            "source_org_id": "RG123",
            "name": "Org",
            "contact_email": "org@example.com",
            "location": "LA, CA",
            "is_active": True,
        }]

        original_time = timezone.now() - timedelta(days=60)
        new_time = timezone.now() - timedelta(days=1)

        # First ingest
        IngestionService.ingest_canonical(org_dicts, [{
            "source": "RESCUEGROUPS",
            "external_id": "P1",
            "organization_source_org_id": "RG123",
            "name": "Bella",
            "species": "DOG",
            "photos": [],
            "raw_description": "",
            "listed_at": original_time,
            "status": "ACTIVE",
        }])

        # Second ingest with a "newer" listed_at (provider changed timestamps)
        IngestionService.ingest_canonical(org_dicts, [{
            "source": "RESCUEGROUPS",
            "external_id": "P1",
            "organization_source_org_id": "RG123",
            "name": "Bella Updated",
            "species": "DOG",
            "photos": [],
            "raw_description": "",
            "listed_at": new_time,
            "status": "ACTIVE",
        }])

        p = Pet.objects.get(source="RESCUEGROUPS", external_id="P1")
        self.assertEqual(p.listed_at, original_time)     # must remain original
        self.assertEqual(p.name, "Bella Updated")         # other fields should still update

