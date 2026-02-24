import json
from django.test import TestCase
from rest_framework.test import APIClient
from django.utils import timezone
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, Application


User = get_user_model()


class ApplicationsListTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="O1",
            name="Test Org",
            contact_email="org@example.com",
            location="LA",
            is_active=True,
        )

        self.pet = Pet.objects.create(
            source="TEST",
            external_id="P1",
            organization=self.org,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            ai_description="ai",
            temperament_tags=[],
            apply_url="https://example.org/apply",
            apply_hint="Apply via Test Org",
        )

        Application.objects.create(
            user=self.user,
            pet=self.pet,
            organization=self.org,
            payload={},
            handoff_payload={
                "version": "v1",
                "type": "APPLICATION_HANDOFF",
                "generated_at": timezone.now().isoformat(),
                "pet": {
                    "apply_url": "https://example.org/apply",
                },
                "disclaimer": {
                    "application_is_not_approval": True,
                },
            },
        )

    def test_list_returns_enveloped_items(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/applications")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        items = payload["data"]["items"]
        self.assertEqual(len(items), 1)

        item = items[0]
        self.assertEqual(item["pet_id"], str(self.pet.pet_id))

        # demo-grade fields
        self.assertIn("apply_url", item)
        self.assertIn("apply_hint", item)
        self.assertEqual(item["apply_url"], "https://example.org/apply")
        self.assertEqual(item["apply_hint"], "Apply via Test Org")

        self.assertIn("email_status", item)
        self.assertIn("created_at", item)

        # mini pet card
        self.assertIn("pet", item)
        self.assertEqual(item["pet"]["pet_id"], str(self.pet.pet_id))
        self.assertEqual(item["pet"]["organization"]["organization_id"], str(self.org.organization_id))

        # handoff summary (whitelisted)
        self.assertIn("handoff", item)
        self.assertEqual(item["handoff"]["version"], "v1")
        self.assertEqual(item["handoff"]["type"], "APPLICATION_HANDOFF")
        self.assertTrue(item["handoff"]["disclaimer"]["application_is_not_approval"])
        self.assertTrue(item["handoff"]["apply_url_present"])