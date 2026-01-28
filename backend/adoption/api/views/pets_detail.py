from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404

from adoption.api.serializers.pets_detail import PetDetailSerializer
from adoption.models import Pet

class PetDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pet_id):
        pet = get_object_or_404(Pet.objects.select_related("organization"), pet_id=pet_id)
        return Response(PetDetailSerializer(pet).data)
