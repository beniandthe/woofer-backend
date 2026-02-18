import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from adoption.models import Pet, Organization, RiskClassification

User = get_user_model()


class FeedDiversityCursorSafeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        org = Organization.objects.create(
            source="TEST",
            source_org_id="O1",
            name="Org",
            contact_email="x@example.com",
            location="X",
            is_active=True,
        )

        # Create 8 boosted + 4 normal, descending listed_at
        for i in range(12):
            pet = Pet.objects.create(
                source="TEST",
                external_id=f"P{i}",
                organization=org,
                name=f"Pet {i}",
                species=Pet.Species.DOG,
                status=Pet.Status.ACTIVE,
                listed_at=timezone.now(),
                photos=[],
                raw_description="",
                temperament_tags=[],
            )
            if i < 8:
                RiskClassification.objects.create(pet=pet, is_long_stay=True)

    def test_page_contains_some_normal_when_available(self):
        resp = self.client.get("/api/v1/pets?limit=10")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        items = payload["data"]["items"]

        # Ensure some are not boosted (why_shown empty)
        normal = [i for i in items if len(i.get("why_shown") or []) == 0]
        self.assertTrue(len(normal) >= 1)

    def test_cursor_pagination_no_duplicates(self):
        resp1 = self.client.get("/api/v1/pets?limit=5")
        payload1 = json.loads(resp1.content.decode("utf-8"))
        ids1 = [i["pet_id"] for i in payload1["data"]["items"]]
        cursor = payload1["data"]["next_cursor"]

        resp2 = self.client.get(f"/api/v1/pets?limit=5&cursor={cursor}")
        payload2 = json.loads(resp2.content.decode("utf-8"))
        ids2 = [i["pet_id"] for i in payload2["data"]["items"]]

        self.assertEqual(len(set(ids1).intersection(set(ids2))), 0)
