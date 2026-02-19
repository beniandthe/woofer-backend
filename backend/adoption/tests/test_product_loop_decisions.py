import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from adoption.models import Pet, Organization, PetSeen

User = get_user_model()


class ProductLoopDecisionTests(TestCase):
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

        self.pet_a = Pet.objects.create(
            source="TEST",
            external_id="a",
            organization=self.org,
            name="Pet A",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )
        self.pet_b = Pet.objects.create(
            source="TEST",
            external_id="b",
            organization=self.org,
            name="Pet B",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def _get_feed_ids(self, limit=10):
        resp = self.client.get(f"/api/v1/pets?limit={limit}")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        items = payload["data"]["items"]
        return [it["pet_id"] for it in items]

    def test_feed_excludes_liked_pets(self):
        # Like pet A
        resp = self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/interest")
        self.assertEqual(resp.status_code, 200)

        ids = self._get_feed_ids(limit=10)
        self.assertNotIn(str(self.pet_a.pet_id), ids)

    def test_feed_excludes_applied_pets(self):
        # Apply pet A
        resp = self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/apply", data={}, format="json")
        self.assertEqual(resp.status_code, 200)

        ids = self._get_feed_ids(limit=10)
        self.assertNotIn(str(self.pet_a.pet_id), ids)

    def test_feed_excludes_passed_pets(self):
        # Pass pet A
        resp = self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/pass")
        self.assertEqual(resp.status_code, 200)

        ids = self._get_feed_ids(limit=10)
        self.assertNotIn(str(self.pet_a.pet_id), ids)

        # And the pass marker should exist
        self.assertTrue(PetSeen.objects.filter(user=self.user, pet=self.pet_a).exists())

    def test_pass_on_liked_pet_is_noop(self):
        # Like pet A
        self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/interest")

        # Attempt pass
        resp = self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/pass")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["status"], "ALREADY_LIKED")
        self.assertFalse(payload["data"]["created"])

        # Ensure no PetSeen record exists for this user/pet
        self.assertFalse(PetSeen.objects.filter(user=self.user, pet=self.pet_a).exists())

    def test_pass_created_flag_true_then_false(self):
        # First pass creates
        resp1 = self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/pass")
        self.assertEqual(resp1.status_code, 200)
        p1 = json.loads(resp1.content.decode("utf-8"))
        self.assertTrue(p1["ok"])
        self.assertEqual(p1["data"]["status"], "PASSED")
        self.assertTrue(p1["data"]["created"])

        # Second pass is idempotent
        resp2 = self.client.post(f"/api/v1/pets/{self.pet_a.pet_id}/pass")
        self.assertEqual(resp2.status_code, 200)
        p2 = json.loads(resp2.content.decode("utf-8"))
        self.assertTrue(p2["ok"])
        self.assertEqual(p2["data"]["status"], "PASSED")
        self.assertFalse(p2["data"]["created"])

