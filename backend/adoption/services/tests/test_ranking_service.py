from django.test import TestCase
from django.utils import timezone
from adoption.models import Organization, Pet, RiskClassification
from adoption.services.ranking_service import RankingService

class RankingServiceTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )

    def test_long_stay_boost_can_outweigh_small_recency_gap(self):
        now = timezone.now()

        # newer pet, no risk
        p_new = Pet.objects.create(
            source="TEST",
            external_id="new",
            organization=self.org,
            name="New",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=now,
            photos=[],
        )

        # slightly older pet, has long stay boost
        p_old = Pet.objects.create(
            source="TEST",
            external_id="old",
            organization=self.org,
            name="Old",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=now - timezone.timedelta(hours=6),
            photos=[],
        )
        RiskClassification.objects.create(pet=p_old, is_long_stay=True)

        ranked = RankingService.rank([p_new, p_old])
        self.assertEqual(ranked[0].pet.pet_id, p_old.pet_id)
        self.assertIn("LONG_STAY_BOOST", ranked[0].reasons)
