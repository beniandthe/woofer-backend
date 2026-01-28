from rest_framework import serializers
from adoption.models import Interest

class InterestsListItemSerializer(serializers.ModelSerializer):
    interest_id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    pet = serializers.SerializerMethodField()

    class Meta:
        model = Interest
        fields = ["interest_id", "created_at", "pet"]

    def get_pet(self, obj):
        pet = obj.pet
        org = pet.organization
        return {
            "pet_id": str(pet.pet_id),
            "name": pet.name,
            "age_group": pet.age_group,
            "size": pet.size,
            "photos": pet.photos,
            "ai_description": pet.ai_description,
            "temperament_tags": pet.temperament_tags,
            "organization": {
                "organization_id": str(org.organization_id),
                "name": org.name,
                "location": org.location,
            },
        }
