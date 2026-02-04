from django.test import SimpleTestCase

from providers.base import ProviderOrg, ProviderPet
from adoption.services.provider_mappers.base import canonical_org_dict, canonical_pet_dict


class ProviderMapperTests(SimpleTestCase):
    def test_org_mapping(self):
        org = ProviderOrg(
            provider="rescuegroups",
            external_org_id="RG123",
            name="Rescue Org",
            contact_email="org@example.com",
            city="Los Angeles",
            state="CA",
            raw={"id": "RG123"},
        )
        d = canonical_org_dict(org)
        self.assertEqual(d["source"], "RESCUEGROUPS")
        self.assertEqual(d["source_org_id"], "RG123")
        self.assertEqual(d["location"], "Los Angeles, CA")
        self.assertTrue(d["is_active"])

    def test_pet_mapping(self):
        pet = ProviderPet(
            provider="rescuegroups",
            external_pet_id="P1",
            external_org_id="RG123",
            name="Bella",
            species="dog",
            status="adoptable",
            listed_at_iso="2026-01-01T00:00:00+00:00",
            photos=["https://example.com/a.jpg"],
            raw_description="Sweet dog",
            raw={"id": "P1"},
        )
        d = canonical_pet_dict(pet)
        self.assertEqual(d["source"], "RESCUEGROUPS")
        self.assertEqual(d["external_id"], "P1")
        self.assertEqual(d["organization_source_org_id"], "RG123")
        self.assertEqual(d["species"], "DOG")
        self.assertEqual(d["status"], "ACTIVE")
        self.assertEqual(d["photos"][0], "https://example.com/a.jpg")
        self.assertEqual(d["raw_description"], "Sweet dog")
