import json
from django.test import TestCase
from rest_framework.test import APIClient

from django.contrib.auth import get_user_model


User = get_user_model()

def parse(resp):
    return json.loads(resp.content.decode("utf-8"))

class ProfileEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_profile_get_creates_default_profile(self):
        resp = self.client.get("/api/v1/profile")
        self.assertEqual(resp.status_code, 200)

        payload = parse(resp)
        self.assertTrue(payload["ok"])

        data = payload["data"]
        self.assertEqual(data["user_id"], str(self.user.id))

        # Default-based optional fields (matches your current behavior)
        self.assertEqual(data["home_type"], "OTHER")
        self.assertEqual(data["activity_level"], "MED")
        self.assertEqual(data["experience_level"], "SOME")

        self.assertFalse(data["has_kids"])
        self.assertFalse(data["has_dogs"])
        self.assertFalse(data["has_cats"])

        self.assertEqual(data["preferences"], {})

    def test_profile_put_partial_update_updates_only_provided_fields(self):
        self.client.get("/api/v1/profile")

        body = {"home_type": "APARTMENT", "has_cats": True, "preferences": {"max_distance_miles": 25}}
        resp = self.client.put("/api/v1/profile", body, format="json")
        self.assertEqual(resp.status_code, 200)

        payload = parse(resp)
        self.assertTrue(payload["ok"])

        data = payload["data"]
        self.assertEqual(data["home_type"], "APARTMENT")
        self.assertTrue(data["has_cats"])
        self.assertEqual(data["preferences"]["max_distance_miles"], 25)

        # Unspecified fields should remain defaults
        self.assertEqual(data["activity_level"], "MED")
        self.assertEqual(data["experience_level"], "SOME")
        self.assertFalse(data["has_kids"])
        self.assertFalse(data["has_dogs"])

    def test_profile_put_rejects_invalid_choice_values(self):
        self.client.get("/api/v1/profile")

        resp = self.client.put("/api/v1/profile", {"home_type": "CASTLE"}, format="json")
        self.assertEqual(resp.status_code, 400)

        payload = parse(resp)
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)

    def test_profile_put_ignores_unknown_fields(self):
        self.client.get("/api/v1/profile")

        resp = self.client.put(
            "/api/v1/profile",
            {"unknown_field": "x", "preferences": {"max_distance_miles": 10}},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        payload = parse(resp)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["preferences"]["max_distance_miles"], 10)
        self.assertNotIn("unknown_field", payload["data"])

