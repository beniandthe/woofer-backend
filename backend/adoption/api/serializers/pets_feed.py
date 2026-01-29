from rest_framework import serializers
from adoption.models import Pet
from adoption.services.ranking_service import RankingService


class PetFeedItemSerializer(serializers.ModelSerializer):
    pet_id = serializers.UUIDField(read_only=True)
    organization = serializers.SerializerMethodField()
    why_shown = serializers.SerializerMethodField()
    
    class Meta:
        model = Pet
        fields = [
            "pet_id",
            "name",
            "age_group",
            "size",
            "photos",
            "ai_description",
            "temperament_tags",
            "organization",
            "why_shown",
        ]

    def get_organization(self, obj):
        org = obj.organization
        return {
            "organization_id": org.organization_id,
            "name": org.name,
            "location": org.location,
        }

    def get_why_shown(self, obj):
        return RankingService.reasons_for_pet(obj)
