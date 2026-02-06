from unittest import mock
from django.core.management import call_command
from django.test import TestCase

from providers.base import ProviderOrg, ProviderPet
from adoption.models import Organization, Pet

from adoption.models import ProviderSyncState

class FakeProvider:
    provider_name = "rescuegroups"

    def iter_orgs(self, *, limit=100, org_id=None):
        yield ProviderOrg(
            provider="rescuegroups",
            external_org_id="RG123",
            name="Test Org",
            contact_email="org@example.com",
            city="Los Angeles",
            state="CA",
            raw={"id": "RG123"},
        )

    def iter_pets(self, *, limit=100, org_id=None):
        yield ProviderPet(
            provider="rescuegroups",
            external_pet_id="P1",
            external_org_id="RG123",
            name="Bella",
            species="DOG",
            age_group="ADULT",
            size="M",
            sex="FEMALE",
            photos=["https://example.com/a.jpg"],
            raw_description="Sweet dog",
            listed_at_iso="2026-01-01T00:00:00+00:00",
            status="available",
            raw={"id": "P1"},
        )

    def test_sync_state_persisted_on_write(self, _mock_factory):
        call_command("ingest_provider", "--provider", "rescuegroups", "--limit", "1")

        state = ProviderSyncState.objects.get(provider="RESCUEGROUPS")
        self.assertIsNotNone(state.last_run_started_at)
        self.assertIsNotNone(state.last_run_finished_at)
        self.assertIsNotNone(state.last_success_at)
        self.assertEqual(state.last_mode, "FULL")

    def test_sync_state_not_persisted_on_dry_run(self, _mock_factory):
        call_command("ingest_provider", "--provider", "rescuegroups", "--limit", "1", "--dry-run")

        self.assertFalse(
            ProviderSyncState.objects.filter(provider="RESCUEGROUPS").exists())


@mock.patch("adoption.management.commands.ingest_provider.get_provider_client", return_value=FakeProvider())
class IngestProviderCommandTests(TestCase):
    def test_dry_run_writes_nothing(self, _mock_factory):
        call_command("ingest_provider", "--provider", "rescuegroups", "--limit", "1", "--dry-run")
        self.assertEqual(Organization.objects.count(), 0)
        self.assertEqual(Pet.objects.count(), 0)

    def test_write_is_idempotent(self, _mock_factory):
        call_command("ingest_provider", "--provider", "rescuegroups", "--limit", "1")
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Pet.objects.count(), 1)

        call_command("ingest_provider", "--provider", "rescuegroups", "--limit", "1")
        self.assertEqual(Organization.objects.count(), 1)
        self.assertEqual(Pet.objects.count(), 1)
