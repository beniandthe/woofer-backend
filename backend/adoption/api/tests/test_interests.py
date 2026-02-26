import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from adoption.models import Organization, Pet, Interest
from django.test import override_settings
from adoption.models import Interest
from django.utils import timezone


class InterestsTests(TestCase):
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
            external_id="p1",
            organization=self.org,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            ai_description="ai",
            temperament_tags=[],
        )

    def test_create_interest_is_enveloped_and_idempotent(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp1 = client.post(f"/api/v1/pets/{self.pet.pet_id}/interest")
        self.assertEqual(resp1.status_code, 200)
        p1 = json.loads(resp1.content.decode("utf-8"))
        self.assertTrue(p1["ok"])
        interest_id_1 = p1["data"]["interest_id"]
        self.assertFalse(p1["data"]["already_existed"])


        resp2 = client.post(f"/api/v1/pets/{self.pet.pet_id}/interest")
        self.assertEqual(resp2.status_code, 200)
        p2 = json.loads(resp2.content.decode("utf-8"))
        self.assertTrue(p2["ok"])
        interest_id_2 = p2["data"]["interest_id"]
        self.assertTrue(p2["data"]["already_existed"])


        # Idempotent - same interest returned
        self.assertEqual(interest_id_1, interest_id_2)

    def test_list_interests_returns_items(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        client.post(f"/api/v1/pets/{self.pet.pet_id}/interest")
        resp = client.get("/api/v1/interests")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        items = payload["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["pet"]["pet_id"], str(self.pet.pet_id))

    def test_interest_create_marks_notification_sent(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.post(f"/api/v1/pets/{self.pet.pet_id}/interest")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        interest_id = payload["data"]["interest_id"]

        interest = Interest.objects.get(interest_id=interest_id)
        self.assertEqual(interest.notification_status, Interest.NotificationStatus.SENT)
        self.assertIsNotNone(interest.notification_attempted_at)

    @override_settings(WOOFER_NOTIFICATIONS_FORCE_FAIL=True)
    def test_notification_failure_does_not_break_interest_create(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.post(f"/api/v1/pets/{self.pet.pet_id}/interest")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        interest_id = payload["data"]["interest_id"]

        interest = Interest.objects.get(interest_id=interest_id)
        self.assertEqual(interest.notification_status, Interest.NotificationStatus.FAILED)
