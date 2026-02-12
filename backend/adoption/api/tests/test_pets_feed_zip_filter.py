import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, AdopterProfile

User = get_user_model()

class PetsFeedZipFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        self.org_match = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org Match",
            contact_email="a@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
        )
        self.org_other = Organization.objects.create(
            source="TEST",
            source_org_id="org2",
            name="Org Other",
            contact_email="b@example.com",
            location="LA",
            is_active=True,
            postal_code="90210",
        )

        self.pet_match = Pet.objects.create(
            source="TEST",
            external_id="p1",
            organization=self.org_match,
            name="Match Pet",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )
        self.pet_other = Pet.objects.create(
            source="TEST",
            external_id="p2",
            organization=self.org_other,
            name="Other Pet",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

    def test_zip_filter_applies_when_home_zip_and_max_distance_present(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = "90012"
        profile.preferences = {"max_distance_miles": 50}
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

    def test_zip_filter_does_not_apply_without_max_distance(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = "90012"
        profile.preferences = {}  # no max distance
        profile.save()

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=50")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        ids = [i["pet_id"] for i in payload["data"]["items"]]
        self.assertIn(str(self.pet_match.pet_id), ids)
        self.assertIn(str(self.pet_other.pet_id), ids)
