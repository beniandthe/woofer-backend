from django.test import TestCase
from django.utils import timezone

from adoption.models import Pet, Organization, RiskClassification
from adoption.services.ranking_service import RankingService, MAX_TOTAL_BOOST


class RankingBoostCapTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Test Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )

    def _make_pet(self, name: str) -> Pet:
        return Pet.objects.create(
            source="TEST",
            external_id=name,
            organization=self.org,
            name=name,
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            temperament_tags=[],
            raw_description="",
        )

    def test_total_boost_is_capped(self):
        pet = self._make_pet("Boosty")
        RiskClassification.objects.create(
            pet=pet,
            is_long_stay=True,
            is_senior=True,
            is_medical=True,
            is_overlooked_breed_group=True,
            recently_returned=True,
        )

        base = RankingService._recency_score(pet.listed_at)
        score, reasons = RankingService.score_pet(pet)

        self.assertTrue(len(reasons) >= 1)
        # Score increase should never exceed cap
        self.assertLessEqual(score - base, MAX_TOTAL_BOOST + 1e-9)

    def test_single_boost_still_applies(self):
        pet = self._make_pet("LongStay")
        RiskClassification.objects.create(
            pet=pet,
            is_long_stay=True,
            is_senior=False,
            is_medical=False,
            is_overlooked_breed_group=False,
            recently_returned=False,
        )

        base = RankingService._recency_score(pet.listed_at)
        score, reasons = RankingService.score_pet(pet)

        self.assertIn("LONG_STAY_BOOST", reasons)
        self.assertGreater(score, base)
        self.assertLessEqual(score - base, MAX_TOTAL_BOOST + 1e-9)


    def test_cap_prevents_permanent_top_lock(self):
        # Two pets with identical listed_at
        t = timezone.now()

        boosted = Pet.objects.create(
            source="TEST",
            external_id="boosted",
            organization=self.org,
            name="Boosted",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=t,
            photos=[],
            temperament_tags=[],
            raw_description="",
        )
        normal = Pet.objects.create(
            source="TEST",
            external_id="normal",
            organization=self.org,
            name="Normal",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=t,
            photos=[],
            temperament_tags=[],
            raw_description="",
        )

        RiskClassification.objects.create(
            pet=boosted,
            is_long_stay=True,
            is_senior=True,
            is_medical=True,
            is_overlooked_breed_group=True,
            recently_returned=True,
        )

        ranked = RankingService.rank([boosted, normal])

        # boosted should still rank above normal (boost helps)
        self.assertEqual(ranked[0].pet.pet_id, boosted.pet_id)

        # but score difference should be capped and not explode
        diff = ranked[0].score - ranked[1].score
        self.assertLessEqual(diff, MAX_TOTAL_BOOST + 1e-9)