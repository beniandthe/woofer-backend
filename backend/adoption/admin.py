from django.contrib import admin
from .models import Organization, Pet, Interest, Application, AdopterProfile, RiskClassification, VisibilityScore

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "source", "source_org_id", "location", "is_active")
    search_fields = ("name", "source_org_id", "contact_email")
    list_filter = ("source", "is_active")

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ("name", "species", "status", "source", "external_id", "organization")
    search_fields = ("name", "external_id", "breed_primary", "breed_secondary")
    list_filter = ("species", "status", "source")

@admin.register(Interest)
class InterestAdmin(admin.ModelAdmin):
    list_display = ("interest_id", "user", "pet", "notification_status", "created_at")
    search_fields = ("user__username", "user__email", "pet__name")
    list_filter = ("notification_status",)

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("application_id", "user", "pet", "organization", "created_at")
    search_fields = ("user__username", "user__email", "pet__name", "organization__name")

@admin.register(AdopterProfile)
class AdopterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "home_type", "has_kids", "has_dogs", "has_cats", "activity_level", "experience_level")

@admin.register(RiskClassification)
class RiskClassificationAdmin(admin.ModelAdmin):
    list_display = ("pet", "is_long_stay", "is_senior", "is_medical", "is_overlooked_breed_group", "recently_returned")

@admin.register(VisibilityScore)
class VisibilityScoreAdmin(admin.ModelAdmin):
    list_display = ("pet", "final_score", "computed_at")
