from django.test import SimpleTestCase
from django.core.management import call_command
from unittest import mock
import sys

class SyncProviderCommandTests(SimpleTestCase):
    @mock.patch("adoption.management.commands.sync_provider.call_command")
    def test_sync_success_exits_zero(self, mock_call):
        mock_call.return_value = None

        with self.assertRaises(SystemExit) as ctx:
            call_command("sync_provider", "--provider", "rescuegroups")

        self.assertEqual(ctx.exception.code, 0)

    @mock.patch("adoption.management.commands.sync_provider.call_command")
    def test_sync_failure_exits_one(self, mock_call):
        mock_call.side_effect = Exception("boom")

        with self.assertRaises(SystemExit) as ctx:
            call_command("sync_provider", "--provider", "rescuegroups")

        self.assertEqual(ctx.exception.code, 1)
