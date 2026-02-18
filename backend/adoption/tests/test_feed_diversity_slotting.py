from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, RiskClassification
from adoption.services.pet_feed_service import PetFeedService

User = get_user_model()

class FeedDiversityTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="feeduser",
            email="feed@example.com",
            password="pass12345",
        )

        org = Organization.objects.create(
            source="TEST",
            source_org_id="O1",
            name="Org",
            contact_email="x@example.com",
            location="X",
            is_active=True,
        )

        # Create boosted pets
        for i in range(5):
            pet = Pet.objects.create(
                source="TEST",
                external_id=f"B{i}",
                organization=org,
                name=f"Boosted {i}",
                species=Pet.Species.DOG,
                status=Pet.Status.ACTIVE,
                listed_at=timezone.now(),
                photos=[],
                raw_description="",
                temperament_tags=[],
            )
            RiskClassification.objects.create(pet=pet, is_long_stay=True)

        # Create normal pets
        for i in range(5):
            Pet.objects.create(
                source="TEST",
                external_id=f"N{i}",
                organization=org,
                name=f"Normal {i}",
                species=Pet.Species.DOG,
                status=Pet.Status.ACTIVE,
                listed_at=timezone.now(),
                photos=[],
                raw_description="",
                temperament_tags=[],
            )

    def test_feed_contains_mix_of_boosted_and_normal(self):
        pets, _ = PetFeedService.get_feed(user=self.user, cursor=None, limit=10)

        names = [p.name for p in pets]
        boosted = [n for n in names if "Boosted" in n]
        normal = [n for n in names if "Normal" in n]

        self.assertGreater(len(boosted), 0)
        self.assertGreater(len(normal), 0)


