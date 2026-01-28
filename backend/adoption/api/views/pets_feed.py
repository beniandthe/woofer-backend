from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from adoption.api.serializers.pets_feed import PetFeedItemSerializer
from adoption.services.pet_feed_service import PetFeedService

class PetsFeedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cursor = request.query_params.get("cursor")
        limit_raw = request.query_params.get("limit")

        limit = None
        if limit_raw is not None:
            try:
                limit = int(limit_raw)
            except ValueError:
                limit = None  # lean MVP: ignore bad limit

        items, next_cursor = PetFeedService.get_feed(request.user, cursor, limit)

        return Response({
            "items": PetFeedItemSerializer(items, many=True).data,
            "next_cursor": next_cursor,
        })
