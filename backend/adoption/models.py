import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone


class Organization(models.Model):
    organization_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.CharField(max_length=50)  # PETFINDER | RESCUEGROUPS (enum later)
    source_org_id = models.CharField(max_length=255)  # provider org id
    name = models.CharField(max_length=255)
    contact_email = models.EmailField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "source_org_id"],
                name="uniq_org_source_provider_id",
            ),
        ]
        indexes = [
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name


class Pet(models.Model):
    class Species(models.TextChoices):
        DOG = "DOG"
        CAT = "CAT"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        INACTIVE = "INACTIVE"

    pet_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    source = models.CharField(max_length=50)  # PETFINDER | RESCUEGROUPS
    external_id = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="pets")

    name = models.CharField(max_length=255)
    species = models.CharField(max_length=10, choices=Species.choices, default=Species.DOG)

    age_group = models.CharField(max_length=20, blank=True, null=True)  # PUPPY|ADULT|SENIOR (enum later)
    size = models.CharField(max_length=5, blank=True, null=True)       # S|M|L|XL (enum later)
    sex = models.CharField(max_length=20, blank=True, null=True)

    breed_primary = models.CharField(max_length=255, blank=True, null=True)
    breed_secondary = models.CharField(max_length=255, blank=True, null=True)
    is_mixed = models.BooleanField(default=False)

    # keep simple for MVP (can normalize later)
    photos = models.JSONField(default=list, blank=True)
    raw_description = models.TextField(blank=True, null=True)
    ai_description = models.TextField(blank=True, null=True)
    temperament_tags = models.JSONField(default=list, blank=True)
    special_needs_flags = models.JSONField(default=list, blank=True)

    listed_at = models.DateTimeField(blank=True, null=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="uniq_pet_source_external_id",
            ),
        ]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["species"]),
            models.Index(fields=["listed_at"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.species})"


class AdopterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="adopter_profile")

    home_type = models.CharField(max_length=50, blank=True, null=True)  # APARTMENT|HOUSE|OTHER
    has_kids = models.BooleanField(default=False)
    has_dogs = models.BooleanField(default=False)
    has_cats = models.BooleanField(default=False)
    activity_level = models.CharField(max_length=20, blank=True, null=True)  # LOW|MED|HIGH
    experience_level = models.CharField(max_length=20, blank=True, null=True)  # NEW|SOME|EXPERIENCED

    preferences = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Interest(models.Model):
    class NotificationStatus(models.TextChoices):
        PENDING = "PENDING"
        SENT = "SENT"
        FAILED = "FAILED"

    interest_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="interests")
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="interests")
    notification_status = models.CharField(max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "pet"], name="uniq_interest_user_pet"),
        ]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["notification_status"]),
        ]


class Application(models.Model):
    """
    Lean MVP: structured handoff record only (not a full workflow).
    """
    application_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="applications")
    pet = models.ForeignKey(Pet, on_delete=models.PROTECT, related_name="applications")
    organization = models.ForeignKey(Organization, on_delete=models.PROTECT, related_name="applications")

    payload = models.JSONField(default=dict, blank=True)  # adopter-entered fields for handoff
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "pet"], name="uniq_application_user_pet"),
        ]
        indexes = [
            models.Index(fields=["created_at"]),
        ]


class RiskClassification(models.Model):
    pet = models.OneToOneField(Pet, on_delete=models.CASCADE, primary_key=True, related_name="risk")

    is_long_stay = models.BooleanField(default=False)
    is_senior = models.BooleanField(default=False)
    is_medical = models.BooleanField(default=False)
    is_overlooked_breed_group = models.BooleanField(default=False)
    recently_returned = models.BooleanField(default=False)

    notes = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)


class VisibilityScore(models.Model):
    pet = models.OneToOneField(Pet, on_delete=models.CASCADE, primary_key=True, related_name="visibility")

    base_score = models.FloatField(default=0.0)
    boost_long_stay = models.FloatField(default=0.0)
    boost_risk = models.FloatField(default=0.0)
    boost_returned = models.FloatField(default=0.0)
    penalty_high_adopt_prob = models.FloatField(default=0.0)  # future
    final_score = models.FloatField(default=0.0)

    computed_at = models.DateTimeField(auto_now=True)


class ProviderSyncState(models.Model):
    """
    Tracks ingestion lifecycle state per provider.
    Canon: lightweight, auditable, no provider schema leakage.
    """

    PROVIDER_CHOICES = [
        ("RESCUEGROUPS", "RescueGroups"),
        # future providers go here
    ]

    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES, unique=True)

    last_run_started_at = models.DateTimeField(null=True, blank=True)
    last_run_finished_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    last_mode = models.CharField(
        max_length=16,
        choices=[("FULL", "Full"), ("INCREMENTAL", "Incremental")],
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.provider} sync state"
