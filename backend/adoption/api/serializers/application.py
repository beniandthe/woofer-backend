from rest_framework import serializers
from adoption.models import Application

class ApplicationCreateRequestSerializer(serializers.Serializer):
    pet_id = serializers.UUIDField()
    organization_id = serializers.UUIDField()
    payload = serializers.DictField(required=False)

class ApplicationCreateResponseSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(read_only=True)
    pet_id = serializers.UUIDField(source="pet.pet_id", read_only=True)
    organization_id = serializers.UUIDField(source="organization.organization_id", read_only=True)

    class Meta:
        model = Application
        fields = ["application_id", "pet_id", "organization_id", "payload", "created_at"]
