from django.test import TestCase
from unittest.mock import patch, call
from django.core.management import call_command


class SyncAllBackfillGeoTests(TestCase):
    @patch("adoption.management.commands.sync_all.call_command")
    def test_sync_all_calls_backfill_by_default(self, mock_call):
        call_command("sync_all", "--provider", "rescuegroups", "--limit", "1", "--dry-run")

        # Confirm order: ingest -> backfill -> enrich
        self.assertGreaterEqual(mock_call.call_count, 3)
        calls = [c.args[0] for c in mock_call.call_args_list]

        self.assertEqual(calls[0], "ingest_provider")
        self.assertEqual(calls[1], "backfill_org_geos")
        self.assertEqual(calls[2], "enrich_pets")

    @patch("adoption.management.commands.sync_all.call_command")
    def test_sync_all_skips_backfill_when_disabled(self, mock_call):
        call_command("sync_all", "--provider", "rescuegroups", "--limit", "1", "--dry-run", "--no-backfill-geo")

        calls = [c.args[0] for c in mock_call.call_args_list]
        self.assertEqual(calls[0], "ingest_provider")
        self.assertEqual(calls[1], "enrich_pets")
        self.assertNotIn("backfill_org_geos", calls)