import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, AdopterProfile

User = get_user_model()

class PetsFeedDistanceBracketTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        # Org/pet in exact ZIP
        self.org_exact = Organization.objects.create(
            source="TEST",
            source_org_id="org_exact",
            name="Org Exact",
            contact_email="a@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
        )
        self.pet_exact = Pet.objects.create(
            source="TEST",
            external_id="p_exact",
            organization=self.org_exact,
            name="Pet Exact",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

        # Org/pet in same ZIP prefix (900xx) but different ZIP
        self.org_prefix = Organization.objects.create(
            source="TEST",
            source_org_id="org_prefix",
            name="Org Prefix",
            contact_email="b@example.com",
            location="LA",
            is_active=True,
            postal_code="90045",
        )
        self.pet_prefix = Pet.objects.create(
            source="TEST",
            external_id="p_prefix",
            organization=self.org_prefix,
            name="Pet Prefix",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

        # Org/pet outside prefix (902xx)
        self.org_far = Organization.objects.create(
            source="TEST",
            source_org_id="org_far",
            name="Org Far",
            contact_email="c@example.com",
            location="LA",
            is_active=True,
            postal_code="90210",
        )
        self.pet_far = Pet.objects.create(
            source="TEST",
            external_id="p_far",
            organization=self.org_far,
            name="Pet Far",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _get_ids(self):
        resp = self.client.get("/api/v1/pets?limit=50")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        return [i["pet_id"] for i in payload["data"]["items"]]

    def test_distance_le_10_exact_zip(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = "90012"
        profile.preferences = {"max_distance_miles": 10}
        profile.save()

        ids = self._get_ids()
        self.assertIn(str(self.pet_exact.pet_id), ids)
        self.assertNotIn(str(self.pet_prefix.pet_id), ids)
        self.assertNotIn(str(self.pet_far.pet_id), ids)

    def test_distance_11_to_50_zip_prefix(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = "90012"
        profile.preferences = {"max_distance_miles": 50}
        profile.save()

        ids = self._get_ids()
        self.assertIn(str(self.pet_exact.pet_id), ids)
        self.assertIn(str(self.pet_prefix.pet_id), ids)
        self.assertNotIn(str(self.pet_far.pet_id), ids)

    def test_distance_gt_50_no_zip_filter(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = "90012"
        profile.preferences = {"max_distance_miles": 51}
        profile.save()

        ids = self._get_ids()
        self.assertIn(str(self.pet_exact.pet_id), ids)
        self.assertIn(str(self.pet_prefix.pet_id), ids)
        self.assertIn(str(self.pet_far.pet_id), ids)
