from rest_framework import serializers
from adoption.models import Application


class ApplicationCreateRequestSerializer(serializers.Serializer):
    organization_id = serializers.UUIDField(required=False, allow_null=True)
    payload = serializers.DictField(required=False)


class ApplicationCreateResponseSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(read_only=True)
    pet_id = serializers.UUIDField(source="pet.pet_id", read_only=True)
    organization_id = serializers.UUIDField(source="organization.organization_id", read_only=True)
    email_status = serializers.CharField(read_only=True)
    apply_url = serializers.CharField(source="pet.apply_url", read_only=True)
    apply_hint = serializers.CharField(source="pet.apply_hint", read_only=True)

    class Meta:
        model = Application
        fields = [
            "application_id",
            "pet_id",
            "organization_id",
            "email_status",
            "payload",
            "apply_url",
            "apply_hint",
            "created_at",
        ]
