from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from adoption.models import Application
from adoption.api.serializers.applications_list import ApplicationsListItemSerializer

class ApplicationsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        apps = (
            Application.objects
            .select_related("pet", "organization")
            .filter(user=request.user)
            .order_by("-created_at")
        )

        return Response({
            "items": ApplicationsListItemSerializer(apps, many=True).data
        })
