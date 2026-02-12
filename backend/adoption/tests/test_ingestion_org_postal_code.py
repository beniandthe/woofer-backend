from django.test import TestCase
from adoption.models import Organization
from adoption.services.ingestion_service import IngestionService

class IngestionOrgPostalCodeTests(TestCase):
    def test_upsert_organization_persists_postal_code(self):
        org_dict = {
            "source": "RESCUEGROUPS",
            "source_org_id": "123",
            "name": "Test Org",
            "contact_email": "org@example.com",
            "location": "Los Angeles, CA",
            "postal_code": "90012",
            "is_active": True,
        }

        org, created = IngestionService.upsert_organization(org_dict)
        self.assertTrue(created)
        self.assertEqual(org.postal_code, "90012")

        # idempotent update
        org_dict["postal_code"] = "90210"
        org2, created2 = IngestionService.upsert_organization(org_dict)
        self.assertFalse(created2)
        self.assertEqual(org2.organization_id, org.organization_id)
        self.assertEqual(org2.postal_code, "90210")

        # sanity: db reflects it
        db_org = Organization.objects.get(source="RESCUEGROUPS", source_org_id="123")
        self.assertEqual(db_org.postal_code, "90210")
