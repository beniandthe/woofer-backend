import json
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from adoption.models import Organization, Pet, PetSeen

User = get_user_model()


class PassFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="pass1234")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.org = Organization.objects.create(
            source="TEST",
            source_org_id="org1",
            name="Org",
            contact_email="o@example.com",
            location="LA",
            is_active=True,
        )
        self.pet1 = Pet.objects.create(
            source="TEST",
            external_id="p1",
            organization=self.org,
            name="Pet 1",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )
        self.pet2 = Pet.objects.create(
            source="TEST",
            external_id="p2",
            organization=self.org,
            name="Pet 2",
            species=Pet.Species.DOG,
            status=Pet.Status.ACTIVE,
            listed_at=timezone.now(),
            photos=[],
            raw_description="",
            temperament_tags=[],
        )

    def test_pass_is_enveloped_and_idempotent(self):
        r1 = self.client.post(f"/api/v1/pets/{self.pet1.pet_id}/pass")
        self.assertEqual(r1.status_code, 200)
        p1 = json.loads(r1.content.decode("utf-8"))
        self.assertTrue(p1["ok"])
        self.assertEqual(p1["data"]["status"], "PASSED")
        self.assertTrue(p1["data"]["created"])

        r2 = self.client.post(f"/api/v1/pets/{self.pet1.pet_id}/pass")
        self.assertEqual(r2.status_code, 200)
        p2 = json.loads(r2.content.decode("utf-8"))
        self.assertTrue(p2["ok"])
        self.assertEqual(p2["data"]["status"], "PASSED")
        self.assertFalse(p2["data"]["created"])

        self.assertEqual(PetSeen.objects.filter(user=self.user, pet=self.pet1).count(), 1)

    def test_pass_excludes_pet_from_feed(self):
        # pass pet1
        self.client.post(f"/api/v1/pets/{self.pet1.pet_id}/pass")

        resp = self.client.get("/api/v1/pets?limit=10")
        self.assertEqual(resp.status_code, 200)
        payload = json.loads(resp.content.decode("utf-8"))
        ids = [i["pet_id"] for i in payload["data"]["items"]]

        self.assertNotIn(str(self.pet1.pet_id), ids)
        self.assertIn(str(self.pet2.pet_id), ids)
