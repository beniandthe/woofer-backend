from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone

from adoption.models import Organization
from adoption.services.ingestion_service import IngestionService


class IngestionGeocodeOrgTests(TestCase):

    @patch("adoption.services.ingestion_service.ZipGeoService.lookup")
    def test_org_with_postal_code_gets_geocoded(self, mock_lookup):
        mock_lookup.return_value = type(
            "Geo", (), {"lat": 34.05, "lon": -118.24}
        )()

        org_data = {
            "source": "TEST",
            "source_org_id": "org1",
            "name": "Test Org",
            "postal_code": "90012",
        }

        org, created = IngestionService.upsert_organization(org_data)

        self.assertTrue(created)
        self.assertEqual(float(org.latitude), 34.05)
        self.assertEqual(float(org.longitude), -118.24)
        self.assertEqual(org.geo_source, "ZIP")
        self.assertIsNotNone(org.geo_updated_at)

    @patch("adoption.services.ingestion_service.ZipGeoService.lookup")
    def test_org_without_postal_code_not_geocoded(self, mock_lookup):
        mock_lookup.return_value = None

        org_data = {
            "source": "TEST",
            "source_org_id": "org2",
            "name": "No Zip Org",
            "postal_code": "",
        }

        org, created = IngestionService.upsert_organization(org_data)

        self.assertTrue(created)
        self.assertIsNone(org.latitude)
        self.assertIsNone(org.longitude)
        self.assertEqual(org.geo_source, "")

    @patch("adoption.services.ingestion_service.ZipGeoService.lookup")
    def test_existing_non_zip_geo_not_overwritten(self, mock_lookup):
        # Create org with non-ZIP geo source
        org = Organization.objects.create(
            source="TEST",
            source_org_id="org3",
            name="Existing Geo Org",
            postal_code="90012",
            latitude=40.0,
            longitude=-70.0,
            geo_source="API",
            geo_updated_at=timezone.now(),
        )

        mock_lookup.return_value = type(
            "Geo", (), {"lat": 34.05, "lon": -118.24}
        )()

        org_data = {
            "source": "TEST",
            "source_org_id": "org3",
            "name": "Existing Geo Org",
            "postal_code": "90012",
        }

        updated_org, created = IngestionService.upsert_organization(org_data)

        self.assertFalse(created)
        self.assertEqual(float(updated_org.latitude), 40.0)
        self.assertEqual(float(updated_org.longitude), -70.0)
        self.assertEqual(updated_org.geo_source, "API")