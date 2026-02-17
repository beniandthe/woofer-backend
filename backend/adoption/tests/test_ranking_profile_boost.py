from django.test import TestCase
from django.utils import timezone

from adoption.models import Organization, Pet, AdopterProfile
from adoption.services.ranking_service import RankingService
from django.contrib.auth import get_user_model


class RankingProfileBoostTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="u1", password="pass1234")

        self.profile = AdopterProfile.objects.create(
            user=self.user,
            home_type=AdopterProfile.HomeType.APARTMENT,
            activity_level=AdopterProfile.ActivityLevel.HIGH,
            experience_level=AdopterProfile.ExperienceLevel.NEW,
            preferences={},
        )

        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="O1",
            name="Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
        )

        self.pet = Pet.objects.create(
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
            ai_description="Friendly, energetic, gentle pup who is easy to love.",
            raw_description="",
            size="S",
        )

    def test_profile_boosts_apply(self):
        score, reasons = RankingService.score_pet(self.pet, profile=self.profile)
        self.assertIn("PROFILE_ACTIVITY_MATCH", reasons)
        self.assertIn("PROFILE_HOME_MATCH", reasons)
        self.assertIn("PROFILE_EXPERIENCE_MATCH", reasons)

    def test_no_profile_no_profile_reasons(self):
        score, reasons = RankingService.score_pet(self.pet, profile=None)
        self.assertNotIn("PROFILE_ACTIVITY_MATCH", reasons)
        self.assertNotIn("PROFILE_HOME_MATCH", reasons)
        self.assertNotIn("PROFILE_EXPERIENCE_MATCH", reasons)

