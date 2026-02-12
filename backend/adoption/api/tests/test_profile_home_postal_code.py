import json
from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()

class ProfileHomePostalCodeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

    def test_put_profile_persists_home_postal_code(self):
        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.put(
            "/api/v1/profile",
            {"home_postal_code": "90012"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["home_postal_code"], "90012")

        resp2 = client.get("/api/v1/profile")
        self.assertEqual(resp2.status_code, 200)

        payload2 = json.loads(resp2.content.decode("utf-8"))
        self.assertTrue(payload2["ok"])
        self.assertEqual(payload2["data"]["home_postal_code"], "90012")
