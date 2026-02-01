from django.test import TestCase
from django.utils import timezone

from adoption.models import Organization, Pet, RiskClassification
from adoption.services.risk_backfill_service import RiskBackfillService


class RiskBackfillServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )

    def test_long_stay_flag(self):
        old = timezone.now() - timezone.timedelta(days=30)
        pet = Pet.objects.create(
            source="TEST",
            external_id="p1",
            organization=self.org,
            name="Oldie",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=old,
            photos=[],
            raw_description="",
            ai_description="",
            temperament_tags=[],
        )

        rc, created = RiskBackfillService.upsert_for_pet(pet)
        self.assertTrue(rc.is_long_stay)
        self.assertFalse(rc.is_medical)

    def test_senior_flag(self):
        pet = Pet.objects.create(
            source="TEST",
            external_id="p2",
            organization=self.org,
            name="Senior",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="",
            ai_description="",
            temperament_tags=[],
            age_group="SENIOR",
        )

        rc, _ = RiskBackfillService.upsert_for_pet(pet)
        self.assertTrue(rc.is_senior)

    def test_medical_keyword_flag(self):
        pet = Pet.objects.create(
            source="TEST",
            external_id="p3",
            organization=self.org,
            name="Med",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="Needs medication daily due to diabetes.",
            ai_description="",
            temperament_tags=[],
        )

        rc, _ = RiskBackfillService.upsert_for_pet(pet)
        self.assertTrue(rc.is_medical)

    def test_idempotent_update_or_create(self):
        pet = Pet.objects.create(
            source="TEST",
            external_id="p4",
            organization=self.org,
            name="Idem",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="",
            ai_description="",
            temperament_tags=[],
        )

        rc1, created1 = RiskBackfillService.upsert_for_pet(pet)
        rc2, created2 = RiskBackfillService.upsert_for_pet(pet)

        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(rc1.pet_id, rc2.pet_id)
        self.assertEqual(RiskClassification.objects.filter(pet=pet).count(), 1)
