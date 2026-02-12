from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from adoption.api.serializers.profile import AdopterProfileSerializer
from adoption.services.user_profile_service import UserProfileService


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = UserProfileService.get_or_create_profile(request.user)
        return Response(AdopterProfileSerializer(profile).data)

    def put(self, request):
        profile = UserProfileService.get_or_create_profile(request.user)
        serializer = AdopterProfileSerializer(profile, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
