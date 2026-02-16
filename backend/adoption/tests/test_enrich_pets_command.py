from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone

from adoption.models import Organization, Pet

class EnrichPetsCommandTests(TestCase):
    def test_backfill_populates_ai_description(self):
        org = Organization.objects.create(
            source="TEST",
            source_org_id="O1",
            name="Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )
        pet = Pet.objects.create(
            source="TEST",
            external_id="P1",
            organization=org,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="Friendly, playful pup who loves cuddles.",
            ai_description=None,
            temperament_tags=[],
        )

        call_command("enrich_pets", "--limit", "10")
        pet.refresh_from_db()
        self.assertTrue(pet.ai_description)
