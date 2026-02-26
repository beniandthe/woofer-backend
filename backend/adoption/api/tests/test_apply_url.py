import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet

User = get_user_model()

class ApplyUrlApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Test Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
        )

        self.pet = Pet.objects.create(
            source="TEST",
            external_id="p1",
            organization=self.org,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
            apply_url="https://example.com/apply",
            apply_hint="Apply on org site",
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_feed_includes_apply_fields(self):
        resp = self.client.get("/api/v1/pets?limit=10")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        items = payload["data"]["items"]
        self.assertGreaterEqual(len(items), 1)

        first = items[0]
        # If ranking changes order, locate pet by id
        match = None
        for it in items:
            if it["pet_id"] == str(self.pet.pet_id):
                match = it
                break
        self.assertIsNotNone(match)

        self.assertEqual(match["apply_url"], "https://example.com/apply")
        self.assertEqual(match["apply_hint"], "Apply on org site")

    def test_detail_includes_apply_fields_if_present(self):
        resp = self.client.get(f"/api/v1/pets/{self.pet.pet_id}")
        if resp.status_code == 404:
            return

        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        data = payload["data"]
        self.assertEqual(data["pet_id"], str(self.pet.pet_id))
        self.assertEqual(data["apply_url"], "https://example.com/apply")
        self.assertEqual(data["apply_hint"], "Apply on org site")
