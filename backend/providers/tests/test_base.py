from django.test import SimpleTestCase
from providers.base import ProviderOrg, ProviderPet


class ProviderBaseTests(SimpleTestCase):
    def test_provider_org_constructs(self):
        org = ProviderOrg(
            provider="rescuegroups",
            external_org_id="RG123",
            name="Test Org",
            contact_email="test@example.com",
            city="Los Angeles",
            state="CA",
            raw={"id": "RG123"},
        )
        self.assertEqual(org.external_org_id, "RG123")
        self.assertEqual(org.provider, "rescuegroups")

    def test_provider_pet_constructs(self):
        pet = ProviderPet(
            provider="rescuegroups",
            external_pet_id="P1",
            external_org_id="RG123",
            name="Bella",
            species="DOG",
            photos=["https://example.com/a.jpg"],
            raw={"id": "P1"},
        )
        self.assertEqual(pet.name, "Bella")
        self.assertEqual(pet.provider, "rescuegroups")
        self.assertEqual(pet.photos[0], "https://example.com/a.jpg")
