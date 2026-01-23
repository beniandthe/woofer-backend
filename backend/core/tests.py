import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

class EnvelopeTests(TestCase):
    def test_health_is_enveloped(self):
        client = APIClient()
        resp = client.get("/api/health", HTTP_ACCEPT="application/json")

        self.assertEqual(resp.status_code, 200)

        body = json.loads(resp.content.decode("utf-8"))

        self.assertEqual(set(body.keys()), {"ok", "data", "meta", "request_id", "timestamp"})
        self.assertTrue(body["ok"])
        self.assertEqual(body["data"], {"status": "ok"})
        self.assertIsInstance(body["meta"], dict)
        self.assertTrue(body["request_id"])
        self.assertTrue(body["timestamp"])
