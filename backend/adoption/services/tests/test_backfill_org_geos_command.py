import io
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from adoption.models import Organization


class BackfillOrgGeosCommandTests(TestCase):
    def setUp(self):
        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org1",
            contact_email="x@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
            latitude=None,
            longitude=None,
            geo_source="",
            geo_updated_at=None,
        )

    @patch("adoption.management.commands.backfill_org_geos.ZipGeoService.lookup")
    def test_writes_geo_when_not_dry_run(self, mock_lookup):
        mock_lookup.return_value = type("R", (), {"lat": 34.0537, "lon": -118.2428})()

        out = io.StringIO()
        call_command("backfill_org_geos", "--limit", "50", stdout=out)

        self.org.refresh_from_db()
        self.assertIsNotNone(self.org.latitude)
        self.assertIsNotNone(self.org.longitude)
        self.assertEqual(self.org.geo_source, "ZIP")
        self.assertIsNotNone(self.org.geo_updated_at)

    @patch("adoption.management.commands.backfill_org_geos.ZipGeoService.lookup")
    def test_dry_run_does_not_write(self, mock_lookup):
        mock_lookup.return_value = type("R", (), {"lat": 34.0537, "lon": -118.2428})()

        out = io.StringIO()
        call_command("backfill_org_geos", "--dry-run", "--limit", "50", stdout=out)

        self.org.refresh_from_db()
        self.assertIsNone(self.org.latitude)
        self.assertIsNone(self.org.longitude)
        self.assertEqual(self.org.geo_source, "")
        self.assertIsNone(self.org.geo_updated_at)