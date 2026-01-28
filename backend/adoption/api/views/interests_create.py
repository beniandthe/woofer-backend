from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from adoption.models import Pet
from adoption.services.interest_service import InterestService
from adoption.api.serializers.interest import InterestCreateResponseSerializer

class PetInterestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pet_id):
        # Ensure pet exists; returns 404 enveloped by exception handler
        get_object_or_404(Pet, pet_id=pet_id)

        interest = InterestService.create_interest(request.user, pet_id)
        return Response(InterestCreateResponseSerializer(interest).data)
