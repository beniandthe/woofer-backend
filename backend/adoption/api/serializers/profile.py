from rest_framework import serializers
from adoption.models import AdopterProfile

class AdopterProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = AdopterProfile
        fields = [
            "user_id",
            "home_type",
            "has_kids",
            "has_dogs",
            "has_cats",
            "activity_level",
            "experience_level",
            "preferences",
        ]
