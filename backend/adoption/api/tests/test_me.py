import json
from django.test import TestCase
from rest_framework.test import APIClient
from accounts.models import User

class MeEndpointTests(TestCase):
    def test_me_requires_auth(self):
        client = APIClient()
        resp = client.get("/api/v1/me")
        self.assertIn(resp.status_code, [401, 403])

        # Validate wire format is still JSON-enveloped on auth errors
        payload = json.loads(resp.content.decode("utf-8"))
        self.assertIn("ok", payload)
        self.assertFalse(payload["ok"])
        self.assertIn("error", payload)
        self.assertIn("request_id", payload)
        self.assertIn("timestamp", payload)

    def test_me_returns_enveloped_identity(self):
        user = User.objects.create_user(username="testuser", password="pass1234", email="t@example.com")
        client = APIClient()
        client.force_authenticate(user=user)

        resp = client.get("/api/v1/me")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))

        # Envelope (wire contract)
        self.assertIn("ok", payload)
        self.assertTrue(payload["ok"])
        self.assertIn("data", payload)
        self.assertIn("meta", payload)
        self.assertIn("request_id", payload)
        self.assertIn("timestamp", payload)

        self.assertEqual(payload["data"]["username"], "testuser")
        self.assertEqual(payload["data"]["email"], "t@example.com")
