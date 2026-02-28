import json
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, AdopterProfile

User = get_user_model()


class PetsFeedZipFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")

        # Home ZIP we will "resolve" via mocked ZipGeoService.lookup
        self.home_zip = "90012"
        self.home_lat = 34.0537
        self.home_lon = -118.2428

        # Org/pet near home (Downtown LA-ish)
        self.org_match = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org Match",
            contact_email="a@example.com",
            location="LA",
            is_active=True,
            postal_code="90012",
            latitude=self.home_lat,
            longitude=self.home_lon,
            geo_source="TEST",
            geo_updated_at=timezone.now(),
        )

        # Far org/pet (Baltimore-ish) so radius filtering is deterministic
        self.org_other = Organization.objects.create(
            source="TEST",
            source_org_id="org2",
            name="Org Other",
            contact_email="b@example.com",
            location="MD",
            is_active=True,
            postal_code="21201",
            latitude=39.2904,
            longitude=-76.6122,
            geo_source="TEST",
            geo_updated_at=timezone.now(),
        )

        self.pet_match = Pet.objects.create(
            source="TEST",
            external_id="p1",
            organization=self.org_match,
            name="Match Pet",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )
        self.pet_other = Pet.objects.create(
            source="TEST",
            external_id="p2",
            organization=self.org_other,
            name="Other Pet",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            last_seen_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

    @patch("adoption.services.pet_feed_service.ZipGeoService.lookup")
    def test_zip_filter_applies_when_home_zip_and_max_distance_present(self, mock_lookup):
        # Force the home centroid lookup to be stable (no CSV dependency)
        mock_lookup.return_value = {"lat": self.home_lat, "lon": self.home_lon}

        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = self.home_zip
        profile.preferences = {"max_distance_miles": 50}
        profile.save()

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=50")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        ids = [i["pet_id"] for i in payload["data"]["items"]]
        self.assertIn(str(self.pet_match.pet_id), ids)
        self.assertNotIn(str(self.pet_other.pet_id), ids)

    def test_zip_filter_does_not_apply_without_max_distance(self):
        profile, _ = AdopterProfile.objects.get_or_create(user=self.user)
        profile.home_postal_code = self.home_zip
        profile.preferences = {}  # no max distance => no distance filter
        profile.save()

        client = APIClient()
        client.force_authenticate(user=self.user)

        resp = client.get("/api/v1/pets?limit=50")
        self.assertEqual(resp.status_code, 200)

        payload = json.loads(resp.content.decode("utf-8"))
        self.assertTrue(payload["ok"])

        ids = [i["pet_id"] for i in payload["data"]["items"]]
        self.assertIn(str(self.pet_match.pet_id), ids)
        self.assertIn(str(self.pet_other.pet_id), ids)
