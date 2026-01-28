import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from adoption.models import Organization, Pet
from django.utils import timezone

class PetsFeedTests(TestCase):
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

        # Ensure deterministic ordering: use controlled listed_at
        now = timezone.now()
        for i in range(5):
            Pet.objects.create(
                source="TEST",
                external_id=f"p{i}",
                organization=self.org,
                name=f"Pet {i}",
                species=Pet.Species.DOG,
                status=Pet.Status.ACTIVE,
                listed_at=now,
                photos=[],
                ai_description="x",
                temperament_tags=[],
            )

    def test_feed_returns_items_and_next_cursor_wire_format(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=2")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)

        data = payload["data"]
        self.assertIn("items", data)
        self.assertEqual(len(data["items"]), 2)
        self.assertIn("next_cursor", data)

    def test_feed_paginates_with_cursor(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        first = client.get("/api/v1/pets?limit=2")
        p1 = json.loads(first.content.decode("utf-8"))
        c = p1["data"]["next_cursor"]
        self.assertIsNotNone(c)

        second = client.get(f"/api/v1/pets?limit=2&cursor={c}")
        p2 = json.loads(second.content.decode("utf-8"))

        self.assertTrue(p2["ok"])
        self.assertEqual(len(p2["data"]["items"]), 2)

        # Ensure no duplicate pet_ids between page 1 and page 2
        ids1 = {item["pet_id"] for item in p1["data"]["items"]}
        ids2 = {item["pet_id"] for item in p2["data"]["items"]}
        self.assertTrue(ids1.isdisjoint(ids2))
