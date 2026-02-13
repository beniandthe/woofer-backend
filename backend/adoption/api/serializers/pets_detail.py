from rest_framework import serializers
from adoption.models import Pet
from adoption.services.ranking_service import RankingService

class PetDetailSerializer(serializers.ModelSerializer):
    pet_id = serializers.UUIDField(read_only=True)
    organization = serializers.SerializerMethodField()
    why_shown = serializers.SerializerMethodField()
    apply_url = serializers.CharField(read_only=True)
    apply_hint = serializers.CharField(read_only=True)

    class Meta:
        model = Pet
        fields = [
            "pet_id",
            "source",
            "external_id",
            "name",
            "species",
            "age_group",
            "size",
            "sex",
            "breed_primary",
            "breed_secondary",
            "is_mixed",
            "photos",
            "raw_description",
            "ai_description",
            "temperament_tags",
            "special_needs_flags",
            "listed_at",
            "last_seen_at",
            "status",
            "why_shown",
            "organization",
            "apply_url",
            "apply_hint",
        ]

    def get_organization(self, obj):
        org = obj.organization
        return {
            "organization_id": org.organization_id,
            "source": org.source,
            "source_org_id": org.source_org_id,
            "name": org.name,
            "contact_email": org.contact_email,
            "location": org.location,
            "is_active": org.is_active,
        }

    def get_why_shown(self, obj):
        return RankingService.reasons_for_pet(obj)
