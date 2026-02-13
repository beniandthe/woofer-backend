from rest_framework import serializers
from adoption.models import Pet
from adoption.services.ranking_service import RankingService


class PetFeedItemSerializer(serializers.ModelSerializer):
    pet_id = serializers.UUIDField(read_only=True)
    organization = serializers.SerializerMethodField()
    why_shown = serializers.SerializerMethodField()
    is_interested = serializers.SerializerMethodField()
    interest_status = serializers.SerializerMethodField()
    apply_url = serializers.CharField(read_only=True)
    apply_hint = serializers.CharField(read_only=True)
    
    
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
            "is_interested",
            "interest_status",
            "apply_url",
            "apply_hint",
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

    def get_is_interested(self, obj):
        interest_map = self.context.get("interest_map", {})
        return str(obj.pet_id) in interest_map

    def get_interest_status(self, obj):
        interest_map = self.context.get("interest_map", {})
        return interest_map.get(str(obj.pet_id))  
