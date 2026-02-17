from django.test import SimpleTestCase
from unittest import mock
from django.core.management import call_command

class SyncAllCommandTests(SimpleTestCase):
    @mock.patch("django.core.management.call_command")
    def test_sync_all_calls_ingest_then_enrich(self, mock_call):
        call_command("sync_all", "--provider", "rescuegroups", "--limit", "10", "--dry-run")

        # Ensure ingest called
        mock_call.assert_any_call("ingest_provider", "--provider", "rescuegroups", "--limit", "10", "--dry-run")
        # Ensure enrich called
        mock_call.assert_any_call("enrich_pets", "--limit", "10", "--dry-run")