import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from adoption.models import Organization, Pet
from django.utils import timezone
from adoption.models import RiskClassification
import uuid

class PetDetailTests(TestCase):
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
            raw_description="raw",
            ai_description="ai",
            temperament_tags=["CALM"],
            special_needs_flags=[],
        )
        RiskClassification.objects.create(pet=self.pet, is_long_stay=True)

    def test_detail_returns_enveloped_pet(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get(f"/api/v1/pets/{self.pet.pet_id}")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        data = payload["data"]
        self.assertEqual(data["pet_id"], str(self.pet.pet_id))
        self.assertEqual(data["name"], "Pet 1")
        self.assertIn("organization", data)
        self.assertEqual(data["organization"]["name"], "Test Org")
        self.assertIn("why_shown", data)
        self.assertIn("LONG_STAY_BOOST", data["why_shown"])

    def test_detail_404_is_enveloped_error(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        missing_id = uuid.uuid4()
        resp = client.get(f"/api/v1/pets/{missing_id}")
        self.assertEqual(resp.status_code, 404)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertIn("ok", payload)
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)
        self.assertIn("request_id", payload)
        self.assertIn("timestamp", payload)
