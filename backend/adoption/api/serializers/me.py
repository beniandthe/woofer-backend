from rest_framework import serializers
from accounts.models import User

class MeSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="id", read_only=True)

    class Meta:
        model = User
        fields = ["user_id", "username", "email", "auth_provider_id", "is_active"]
