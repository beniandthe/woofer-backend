from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from adoption.models import Organization, Pet, PetExposureStats
from adoption.services.pet_exposure_service import PetExposureService


class PetExposureStatsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="exposure_user", password="pw")

        # Organization: source, source_org_id, name
        self.org = Organization.objects.create(
            source="RESCUEGROUPS",
            source_org_id="org_1",
            name="Test Org",
        )
        # Pet: source, external_id, organization, name (species has a default)
        self.pet = Pet.objects.create(
            source="RESCUEGROUPS",
            external_id="pet_1",
            organization=self.org,
            name="Test Pet",
        )

    def test_unique_constraint_user_pet(self):
        PetExposureStats.objects.create(user=self.user, pet=self.pet)
        with self.assertRaises(IntegrityError):
            PetExposureStats.objects.create(user=self.user, pet=self.pet)

    def test_bump_impression_creates_then_increments(self):
        now = timezone.now()

        r1 = PetExposureService.bump_impression(self.user, self.pet, at=now)
        stats = PetExposureStats.objects.get(pk=r1.stats_id)
        self.assertTrue(r1.created)
        self.assertEqual(stats.impressions_count, 1)
        self.assertEqual(stats.last_impression_at, now)

        r2 = PetExposureService.bump_impression(self.user, self.pet, at=now)
        stats.refresh_from_db()
        self.assertFalse(r2.created)  # row already existed
        self.assertEqual(stats.impressions_count, 2)
        self.assertEqual(stats.last_impression_at, now)

    def test_bump_like_apply_pass_increment_safely(self):
        PetExposureService.bump_like(self.user, self.pet)
        PetExposureService.bump_apply(self.user, self.pet)
        PetExposureService.bump_pass(self.user, self.pet)

        stats = PetExposureStats.objects.get(user=self.user, pet=self.pet)
        self.assertEqual(stats.likes_count, 1)
        self.assertEqual(stats.applies_count, 1)
        self.assertEqual(stats.passes_count, 1)

    def test_get_or_create_is_deterministic(self):
        stats1, created1 = PetExposureService.get_or_create(self.user, self.pet)
        stats2, created2 = PetExposureService.get_or_create(self.user, self.pet)
        self.assertTrue(created1)
        self.assertFalse(created2)
        self.assertEqual(stats1.pk, stats2.pk)