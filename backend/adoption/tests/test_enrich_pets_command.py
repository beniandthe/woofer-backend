import io
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone

from adoption.models import Organization, Pet

class EnrichPetsCommandTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="O1",
            name="Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
        )

    def test_enrich_only_missing_ai_description(self):
        p1 = Pet.objects.create(
            source="TEST",
            external_id="P1",
            organization=self.org,
            name="Bella",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            temperament_tags=[],
            ai_description=None,
            raw_description="Sweet dog",
        )

        p2 = Pet.objects.create(
            source="TEST",
            external_id="P2",
            organization=self.org,
            name="AlreadyDone",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            temperament_tags=[],
            ai_description="Existing",
            raw_description="",
        )

        out = io.StringIO()
        call_command("enrich_pets", "--limit", "50", stdout=out)

        p1.refresh_from_db()
        p2.refresh_from_db()

        self.assertIsNotNone(p1.ai_description)
        self.assertNotEqual(p1.ai_description, "")
        self.assertEqual(p2.ai_description, "Existing")  # no overwrite

        self.assertIn("Enrichment backfill complete:", out.getvalue())

    def test_enrich_respects_limit(self):
        Pet.objects.create(
            source="TEST",
            external_id="P1",
            organization=self.org,
            name="One",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            temperament_tags=[],
            ai_description=None,
            raw_description="Friendly, playful pup who loves cuddles.",
        )

        Pet.objects.create(
            source="TEST",
            external_id="P2",
            organization=self.org,
            name="Two",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            temperament_tags=[],
            ai_description=None,
            raw_description="Sweet dog who enjoys walks and naps.",
        )

        call_command("enrich_pets", "--limit", "1")
        enriched = Pet.objects.filter(ai_description__isnull=False).exclude(ai_description="").count()
        self.assertEqual(enriched, 1)

    def test_dry_run_writes_nothing(self):
        p = Pet.objects.create(
            source="TEST",
            external_id="P1",
            organization=self.org,
            name="DryRunDog",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            temperament_tags=[],
            ai_description=None,
            raw_description="",
        )

        call_command("enrich_pets", "--limit", "10", "--dry-run")

        p.refresh_from_db()
        self.assertIsNone(p.ai_description)
