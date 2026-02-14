from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from adoption.models import Pet
from adoption.services.application_service import ApplicationService
from adoption.api.serializers.application import ApplicationCreateResponseSerializer


class PetApplyCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pet_id: str):

        body = request.data or {}
        payload = body.get("payload") or {}
        organization_id = body.get("organization_id")
        
        app = ApplicationService.create_application(
            user=request.user,
            pet_id=str(pet_id),
            payload=payload,
            organization_id=organization_id,
        )

        return Response(ApplicationCreateResponseSerializer(app).data)
