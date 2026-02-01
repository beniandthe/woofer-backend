from django.test import TestCase
from adoption.models import Organization, Pet
from adoption.services.ingestion_service import IngestionService
from adoption.services.petfinder_mapper import SOURCE_PETFINDER


class IngestionServiceTests(TestCase):
    def test_ingest_petfinder_is_idempotent(self):
        org_payloads = [
            {
                "id": "CA123",
                "name": "Test Rescue",
                "email": "rescue@example.com",
                "address": {"city": "Los Angeles", "state": "CA"},
            }
        ]

        animal_payloads = [
            {
                "id": 111,
                "name": "Bella",
                "species": "Dog",
                "organization_id": "CA123",
                "description": "Sweet dog",
                "status": "adoptable",
                "photos": [{"full": "https://example.com/a.jpg"}],
                "published_at": "2026-01-01T00:00:00+00:00",
            }
        ]

        r1 = IngestionService.ingest_petfinder(org_payloads, animal_payloads)
        self.assertEqual(r1.organizations_created, 1)
        self.assertEqual(r1.pets_created, 1)

        r2 = IngestionService.ingest_petfinder(org_payloads, animal_payloads)
        self.assertEqual(r2.organizations_created, 0)
        self.assertEqual(r2.organizations_updated, 1)
        self.assertEqual(r2.pets_created, 0)
        self.assertEqual(r2.pets_updated, 1)

        org = Organization.objects.get(source=SOURCE_PETFINDER, source_org_id="CA123")
        self.assertEqual(org.name, "Test Rescue")

        pet = Pet.objects.get(source=SOURCE_PETFINDER, external_id="111")
        self.assertEqual(pet.name, "Bella")
        self.assertEqual(pet.status, "ACTIVE")
        self.assertEqual(pet.organization_id, org.organization_id)

    def test_missing_org_id_skips_pet(self):
        org_payloads = [
            {"id": "CA123", "name": "Test Rescue", "address": {"city": "LA", "state": "CA"}}
        ]

        animal_payloads = [
            {"id": 222, "name": "NoOrgPet", "species": "Dog", "status": "adoptable"}
        ]

        r = IngestionService.ingest_petfinder(org_payloads, animal_payloads)
        self.assertEqual(r.pets_created, 0)
        self.assertEqual(r.pets_skipped, 1)
        self.assertEqual(Pet.objects.count(), 0)
