from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

class EnvelopeTests(TestCase):
    def test_health_is_enveloped(self):
        client = APIClient()
        resp = client.get("/api/health")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ok", resp.data)
        self.assertIn("data", resp.data)
        self.assertIn("meta", resp.data)
        self.assertIn("request_id", resp.data)
        self.assertIn("timestamp", resp.data)
        self.assertTrue(resp.data["ok"])
