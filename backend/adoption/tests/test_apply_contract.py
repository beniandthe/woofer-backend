import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet

User = get_user_model()


class ApplyContractTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Test Org",
            contact_email="o@example.com",
            location="LA",
            postal_code="90012",
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
            temperament_tags=[],
            apply_url="https://example.org/apply",
            apply_hint="Complete the form",
        )

    def test_apply_response_is_enveloped_and_has_required_fields(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.post(
            f"/api/v1/pets/{self.pet.pet_id}/apply",
            data={"payload": {}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        # Canon: parse JSON from resp.content to avoid DRF abstraction drift
        payload = json.loads(resp.content.decode("utf-8"))

        self.assertIn("ok", payload)
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)

        data = payload["data"]

        # Required fields
        for key in [
            "application_id",
            "pet_id",
            "organization_id",
            "email_status",
            "payload",
            "apply_url",
            "apply_hint",
            "created_at",
        ]:
            self.assertIn(key, data)

        # Sanity: ids match
        self.assertEqual(data["pet_id"], str(self.pet.pet_id))
        self.assertEqual(data["organization_id"], str(self.org.organization_id))

        # apply_url/hint should echo from pet
        self.assertEqual(data["apply_url"], self.pet.apply_url)
        self.assertEqual(data["apply_hint"], self.pet.apply_hint)
