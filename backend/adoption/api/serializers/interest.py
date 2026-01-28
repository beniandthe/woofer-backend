from rest_framework import serializers
from adoption.models import Interest

class InterestCreateResponseSerializer(serializers.ModelSerializer):
    interest_id = serializers.UUIDField(read_only=True)
    pet_id = serializers.UUIDField(source="pet.pet_id", read_only=True)
    status = serializers.CharField(source="notification_status", read_only=True)

    class Meta:
        model = Interest
        fields = ["interest_id", "pet_id", "status"]
