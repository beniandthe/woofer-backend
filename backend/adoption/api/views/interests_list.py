from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from adoption.services.interest_service import InterestService
from adoption.api.serializers.interests_list import InterestsListItemSerializer

class InterestsListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        interests = InterestService.list_interests(request.user)
        return Response({
            "items": InterestsListItemSerializer(interests, many=True).data
        })
