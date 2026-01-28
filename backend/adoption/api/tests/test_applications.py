import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User
from adoption.models import Organization, Pet
from django.utils import timezone

class ApplicationsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        self.org1 = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org 1",
            contact_email="o1@example.com",
            location="LA",
            is_active=True,
        )
        self.org2 = Organization.objects.create(
            source="TEST",
            source_org_id="org2",
            name="Org 2",
            contact_email="o2@example.com",
            location="LA",
            is_active=True,
        )
        self.pet = Pet.objects.create(
            source="TEST",
            external_id="p1",
            organization=self.org1,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            ai_description="ai",
            temperament_tags=[],
        )

    def test_create_application_is_enveloped_and_idempotent(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        body = {
            "pet_id": str(self.pet.pet_id),
            "organization_id": str(self.org1.organization_id),
            "payload": {"field": "value"},
        }

        resp1 = client.post("/api/v1/applications", body, format="json")
        self.assertEqual(resp1.status_code, 200)
        p1 = json.loads(resp1.content.decode("utf-8"))
        self.assertTrue(p1["ok"])
        app_id_1 = p1["data"]["application_id"]

        resp2 = client.post("/api/v1/applications", body, format="json")
        self.assertEqual(resp2.status_code, 200)
        p2 = json.loads(resp2.content.decode("utf-8"))
        self.assertTrue(p2["ok"])
        app_id_2 = p2["data"]["application_id"]

        self.assertEqual(app_id_1, app_id_2)

    def test_application_rejects_org_mismatch(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        body = {
            "pet_id": str(self.pet.pet_id),
            "organization_id": str(self.org2.organization_id),  # mismatch
            "payload": {"field": "value"},
        }

        resp = client.post("/api/v1/applications", body, format="json")
        self.assertEqual(resp.status_code, 400)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)
        # details should include the serializer/validation error payload
        self.assertIn("details", payload["error"])
