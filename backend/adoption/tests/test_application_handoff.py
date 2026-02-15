import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model
from adoption.models import Organization, Pet, Application, AdopterProfile

User = get_user_model()


class ApplicationHandoffTests(TestCase):
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
            ai_description="ai",
            temperament_tags=[],
            apply_url="https://example.org/apply",
            apply_hint="Fill out the form",
        )
        # ensure profile exists with prefs
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.preferences = {"max_distance_miles": 50}
        # if you have this field
        if hasattr(profile, "home_postal_code"):
            profile.home_postal_code = "90012"
        profile.save()

    def test_application_persists_profile_snapshot_and_handoff(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.post(f"/api/v1/pets/{self.pet.pet_id}/apply", data={"payload": {}}, format="json")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        app_id = payload["data"]["application_id"]

        app = Application.objects.get(application_id=app_id)
        self.assertIn("preferences", app.profile_snapshot)
        self.assertEqual(app.profile_snapshot["preferences"].get("max_distance_miles"), 50)

        self.assertEqual(app.handoff_payload.get("version"), "v1")
        self.assertEqual(app.handoff_payload["pet"]["pet_id"], str(self.pet.pet_id))
        self.assertEqual(app.handoff_payload["organization"]["organization_id"], str(self.org.organization_id))
        self.assertTrue(app.handoff_payload["disclaimer"]["application_is_not_approval"])

    def test_application_is_idempotent_same_application(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        r1 = client.post(f"/api/v1/pets/{self.pet.pet_id}/apply", data={"payload": {}}, format="json")
        r2 = client.post(f"/api/v1/pets/{self.pet.pet_id}/apply", data={"payload": {}}, format="json")

        p1 = json.loads(r1.content.decode("utf-8"))
        p2 = json.loads(r2.content.decode("utf-8"))
        self.assertEqual(p1["data"]["application_id"], p2["data"]["application_id"])
