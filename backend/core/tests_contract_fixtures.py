import json
from pathlib import Path
from django.test import TestCase

class ContractFixtureEnvelopeTests(TestCase):
    def test_all_contract_fixtures_are_enveloped(self):
        root = Path(__file__).resolve().parent.parent / "contracts" / "v1"
        for p in root.glob("*.json"):
            payload = json.loads(p.read_text(encoding="utf-8"))
            self.assertIn("ok", payload, msg=f"{p.name} missing ok")
            self.assertIn("request_id", payload, msg=f"{p.name} missing request_id")
            self.assertIn("timestamp", payload, msg=f"{p.name} missing timestamp")
            self.assertTrue(("data" in payload) ^ ("error" in payload), msg=f"{p.name} must have data or error")
