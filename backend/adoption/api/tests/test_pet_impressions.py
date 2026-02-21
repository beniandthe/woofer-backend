import json
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, PetExposureStats, PetImpression


User = get_user_model()


class PetImpressionRecordingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="imp_u", password="pass1234")

        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Test Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )

        now = timezone.now()
        self.pets = []
        for i in range(5):
            self.pets.append(
                Pet.objects.create(
                    source="TEST",
                    external_id=f"p{i}",
                    organization=self.org,
                    name=f"Pet {i}",
                    species=Pet.Species.DOG,
                    status=Pet.Status.ACTIVE,
                    listed_at=now,
                    last_seen_at=now,
                    photos=[],
                    raw_description="",
                    temperament_tags=[],
                    ai_description="x",
                )
            )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_feed_records_impressions_once_per_cursor_and_limit(self):
        # First page
        r1 = self.client.get("/api/v1/pets?limit=2")
        self.assertEqual(r1.status_code, 200)
        p1 = json.loads(r1.content.decode("utf-8"))
        self.assertTrue(p1["ok"])

        items1 = p1["data"]["items"]
        self.assertEqual(len(items1), 2)
        ids1 = [i["pet_id"] for i in items1]
        next_cursor = p1["data"]["next_cursor"]
        self.assertIsNotNone(next_cursor)

        # After first page: impressions_count should be 1 for those pets
        for pid in ids1:
            stats = PetExposureStats.objects.get(user=self.user, pet_id=pid)
            self.assertEqual(stats.impressions_count, 1)

        # Re-fetch the SAME first page (same cursor key = "" and same effective limit)
        r1b = self.client.get("/api/v1/pets?limit=2")
        self.assertEqual(r1b.status_code, 200)
        p1b = json.loads(r1b.content.decode("utf-8"))
        self.assertTrue(p1b["ok"])
        ids1b = [i["pet_id"] for i in p1b["data"]["items"]]
        self.assertEqual(ids1b, ids1)  # deterministic feed slice

        # Still should be 1 (no double count)
        for pid in ids1:
            stats = PetExposureStats.objects.get(user=self.user, pet_id=pid)
            self.assertEqual(stats.impressions_count, 1)

        # Second page should record impressions for new pets
        r2 = self.client.get(f"/api/v1/pets?limit=2&cursor={next_cursor}")
        self.assertEqual(r2.status_code, 200)
        p2 = json.loads(r2.content.decode("utf-8"))
        self.assertTrue(p2["ok"])
        items2 = p2["data"]["items"]
        self.assertEqual(len(items2), 2)
        ids2 = [i["pet_id"] for i in items2]

        # Should not overlap due to cursor paging
        self.assertTrue(set(ids1).isdisjoint(set(ids2)))

        for pid in ids2:
            stats = PetExposureStats.objects.get(user=self.user, pet_id=pid)
            self.assertEqual(stats.impressions_count, 1)

        # Ledger rows exist exactly once per key
        # first page cursor key == "" (blank)
        self.assertEqual(
            PetImpression.objects.filter(
                user=self.user,
                page_cursor_key="",
                page_limit=2,
                pet_id__in=ids1,
            ).count(),
            2,
        )