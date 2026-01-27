import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User

class ProfileEndpointTests(TestCase):
    def test_profile_get_creates_default(self):
        user = User.objects.create_user(username="u1", password="pass1234")
        client = APIClient()
        client.force_authenticate(user=user)

        resp = client.get("/api/v1/profile")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["user_id"], str(user.id))

    def test_profile_put_updates_allowed_fields(self):
        user = User.objects.create_user(username="u2", password="pass1234")
        client = APIClient()
        client.force_authenticate(user=user)

        body = {"home_type": "APARTMENT", "has_cats": True, "preferences": {"max_distance_miles": 25}}
        resp = client.put("/api/v1/profile", body, format="json")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["home_type"], "APARTMENT")
        self.assertTrue(payload["data"]["has_cats"])
        self.assertEqual(payload["data"]["preferences"]["max_distance_miles"], 25)

    def test_profile_put_ignores_unknown_fields(self):
        user = User.objects.create_user(username="u3", password="pass1234")
        client = APIClient()
        client.force_authenticate(user=user)

        body = {"unknown_field": "x", "preferences": {"max_distance_miles": 10}}
        resp = client.put("/api/v1/profile", body, format="json")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["preferences"]["max_distance_miles"], 10)
        self.assertNotIn("unknown_field", payload["data"])
