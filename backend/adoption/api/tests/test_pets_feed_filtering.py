import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Pet, Organization, AdopterProfile

User = get_user_model()

class PetsFeedFilteringTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")
        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Test Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )

        # Pet that SHOULD match constraints
        self.pet_match = Pet.objects.create(
            source="TEST",
            external_id="p_match",
            organization=self.org,
            name="Match Pet",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            size="S",
            age_group="ADULT",
            photos=[],
            raw_description="",
            temperament_tags=["GOOD_WITH_CATS"],
        )

        # Pet that should be filtered out
        self.pet_other = Pet.objects.create(
            source="TEST",
            external_id="p_other",
            organization=self.org,
            name="Other Pet",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            size="L",
            age_group="SENIOR",
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

    def test_preferred_sizes_filters_feed(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.preferences = {"preferred_sizes": ["S"]}
        profile.save()

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=50")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        ids = [i["pet_id"] for i in payload["data"]["items"]]
        self.assertIn(str(self.pet_match.pet_id), ids)
        self.assertNotIn(str(self.pet_other.pet_id), ids)

    def test_hard_constraints_filter_by_temperament_tag(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.preferences = {"hard_constraints": ["GOOD_WITH_CATS"]}
        profile.save()

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=50")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        ids = [i["pet_id"] for i in payload["data"]["items"]]
        self.assertIn(str(self.pet_match.pet_id), ids)
        self.assertNotIn(str(self.pet_other.pet_id), ids)
