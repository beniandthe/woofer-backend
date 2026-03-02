from django.test import SimpleTestCase
from unittest import mock
from django.core.management import call_command
from unittest.mock import patch

class SyncAllCommandTests(SimpleTestCase):
    @patch("adoption.management.commands.sync_all.call_command")
    def test_sync_all_calls_ingest_then_backfill_then_enrich_by_default(self, mock_call):
        # This calls the real sync_all command, but all nested commands are mocked
        call_command("sync_all", "--provider", "rescuegroups", "--limit", "10", "--dry-run")

        # Verify the nested commands were invoked in order
        calls = [c.args[0] for c in mock_call.call_args_list]

        self.assertGreaterEqual(len(calls), 3)
        self.assertEqual(calls[0], "ingest_provider")
        self.assertEqual(calls[1], "backfill_org_geos")
        self.assertEqual(calls[2], "enrich_pets")

    @patch("adoption.management.commands.sync_all.call_command")
    def test_sync_all_skips_backfill_when_disabled(self, mock_call):
        call_command(
            "sync_all",
            "--provider", "rescuegroups",
            "--limit", "10",
            "--dry-run",
            "--no-backfill-geo",
        )

        calls = [c.args[0] for c in mock_call.call_args_list]

        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(calls[0], "ingest_provider")
        self.assertEqual(calls[1], "enrich_pets")
        self.assertNotIn("backfill_org_geos", calls)