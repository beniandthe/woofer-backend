from rest_framework import serializers
from adoption.models import Application


class ApplicationsListItemSerializer(serializers.ModelSerializer):
    application_id = serializers.UUIDField(read_only=True)
    pet_id = serializers.UUIDField(source="pet.pet_id", read_only=True)
    organization_id = serializers.UUIDField(source="organization.organization_id", read_only=True)
    pet_name = serializers.CharField(source="pet.name", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True)
    organization_location = serializers.CharField(source="organization.location", read_only=True)
    email_status = serializers.CharField(read_only=True)
    apply_url = serializers.CharField(source="pet.apply_url", read_only=True)
    apply_hint = serializers.CharField(source="pet.apply_hint", read_only=True)

    pet = serializers.SerializerMethodField()
    handoff = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = [
            "application_id",
            "pet_id",
            "pet_name",
            "organization_id",
            "organization_name",
            "organization_location",
            "email_status",
            "created_at",
            "apply_url",
            "apply_hint",
            "pet",
            "handoff",
        ]

    def get_pet(self, obj):
        pet = obj.pet
        org = obj.organization
        # mini-card only (demo-grade)
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

    def get_handoff(self, obj):
        # Whitelist only the parts to expose in list views
        hp = obj.handoff_payload or {}

        disclaimer = hp.get("disclaimer") or {}
        pet = hp.get("pet") or {}

        return {
            "version": hp.get("version"),
            "type": hp.get("type"),
            "generated_at": hp.get("generated_at"),
            "disclaimer": {
                "application_is_not_approval": bool(disclaimer.get("application_is_not_approval", False)),
            },
            "apply_url_present": bool(pet.get("apply_url") or obj.pet.apply_url),
        }