import json
from django.test import TestCase, override_settings
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

class DevAuthFenceTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def _parse(self, resp):
        return json.loads(resp.content.decode("utf-8"))

    @override_settings(DEBUG=True, WOOFER_DEV_AUTH=True, WOOFER_ALLOW_DEV_AUTH=False)
    def test_dev_header_auth_disabled_by_default(self):
        resp = self.client.get("/api/v1/me", HTTP_X_WOOFER_DEV_USER="fence_user")
        payload = self._parse(resp)

        self.assertIn(resp.status_code, (401, 403))
        self.assertFalse(payload["ok"])
        self.assertIn(payload["error"]["code"], ("UNAUTHORIZED", "FORBIDDEN"))
        self.assertIn("error", payload)
        self.assertNotIn("data", payload)

    @override_settings(DEBUG=True, WOOFER_DEV_AUTH=True, WOOFER_ALLOW_DEV_AUTH=True)
    def test_dev_header_auth_enabled_when_allow_flag_on(self):
        resp = self.client.get("/api/v1/me", HTTP_X_WOOFER_DEV_USER="fence_user")
        payload = self._parse(resp)

        self.assertEqual(resp.status_code, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["username"], "fence_user")

    @override_settings(DEBUG=False, WOOFER_DEV_AUTH=True, WOOFER_ALLOW_DEV_AUTH=True)
    def test_dev_header_auth_never_works_when_debug_false(self):
        resp = self.client.get("/api/v1/me", HTTP_X_WOOFER_DEV_USER="fence_user")
        payload = self._parse(resp)

        self.assertIn(resp.status_code, (401, 403))
        self.assertFalse(payload["ok"])
        self.assertIn(payload["error"]["code"], ("UNAUTHORIZED", "FORBIDDEN"))
        self.assertIn("error", payload)
        self.assertNotIn("data", payload)