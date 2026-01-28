from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from adoption.api.serializers.application import (
    ApplicationCreateRequestSerializer,
    ApplicationCreateResponseSerializer,
)
from adoption.services.application_service import ApplicationService

class ApplicationsCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ser = ApplicationCreateRequestSerializer(data=request.data or {})
        ser.is_valid(raise_exception=True)

        app = ApplicationService.create_application(
            user=request.user,
            pet_id=ser.validated_data["pet_id"],
            organization_id=ser.validated_data["organization_id"],
            payload=ser.validated_data.get("payload", {}),
        )
        return Response(ApplicationCreateResponseSerializer(app).data)
