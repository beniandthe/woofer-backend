from unittest import mock
from django.core.management import call_command
from django.test import TestCase

from providers.base import ProviderOrg, ProviderPet
from adoption.models import Organization, Pet


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
