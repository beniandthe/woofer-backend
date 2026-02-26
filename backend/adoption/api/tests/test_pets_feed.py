import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from adoption.models import Organization, Pet, RiskClassification, Interest
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

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
        self.pet = Pet.objects.create(
            source="TEST",
            external_id="p1a",
            organization=self.org,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )


    def test_feed_is_enveloped_and_paginates_with_cursor(self):
        now = timezone.now()

        # Create several pets so pagination is meaningful
        for i in range(6):
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

        client = APIClient()
        client.force_authenticate(user=self.user)

        first = client.get("/api/v1/pets?limit=2")
        self.assertEqual(first.status_code, 200)
        p1 = json.loads(first.content.decode("utf-8"))
        self.assertTrue(p1["ok"])

        c = p1["data"]["next_cursor"]
        self.assertIsNotNone(c)

        second = client.get(f"/api/v1/pets?limit=2&cursor={c}")
        self.assertEqual(second.status_code, 200)
        p2 = json.loads(second.content.decode("utf-8"))
        self.assertTrue(p2["ok"])

        ids1 = {item["pet_id"] for item in p1["data"]["items"]}
        ids2 = {item["pet_id"] for item in p2["data"]["items"]}
        self.assertTrue(ids1.isdisjoint(ids2))

    def test_feed_excludes_interested_pets(self):
        # Create interest for this user+pet
        Interest.objects.create(
            user=self.user,
            pet=self.pet,
            notification_status=Interest.NotificationStatus.SENT,
        )

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=10")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        items = payload["data"]["items"]
        ids = [i["pet_id"] for i in items]

        # liked pets do not appear in feed
        self.assertNotIn(str(self.pet.pet_id), ids)



    def test_ranking_boost_affects_feed_order(self):
        now = timezone.now()

        # Newer pet, no risk
        p_new = Pet.objects.create(
            source="TEST",
            external_id="new",
            organization=self.org,
            name="New",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=now,
            photos=[],
            ai_description="x",
            temperament_tags=[],
        )

        # Slightly older pet but long-stay boost should push it above
        p_old = Pet.objects.create(
            source="TEST",
            external_id="old",
            organization=self.org,
            name="Old",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=now - timezone.timedelta(hours=6),
            photos=[],
            ai_description="x",
            temperament_tags=[],
        )
        RiskClassification.objects.create(pet=p_old, is_long_stay=True)

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=10")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        items = payload["data"]["items"]
        self.assertIn("why_shown", items[0])
        self.assertIn("LONG_STAY_BOOST", items[0]["why_shown"])

        # Top item should be boosted old pet
        self.assertEqual(items[0]["pet_id"], str(p_old.pet_id))
