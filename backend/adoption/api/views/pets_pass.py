from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from adoption.services.pet_seen_service import PetSeenService
from adoption.models import Pet, Interest, Application



class PetPassView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pet_id: str):
        pet = get_object_or_404(Pet, pet_id=pet_id)

        if Interest.objects.filter(user=request.user, pet=pet).exists():
            return Response(
                {
                    "pet_id": str(pet.pet_id),
                    "status": "ALREADY_LIKED",
                    "created": False,
                },
                status=status.HTTP_200_OK,
            )

        if Application.objects.filter(user=request.user, pet=pet).exists():
            return Response(
                {
                    "pet_id": str(pet.pet_id),
                    "status": "ALREADY_APPLIED",
                    "created": False,
                },
                status=status.HTTP_200_OK,
            )

        seen, created = PetSeenService.mark_seen(request.user, pet_id)

        return Response(
            {
                "pet_id": str(seen.pet.pet_id),
                "status": "PASSED",
                "created": created,
            },
            status=status.HTTP_200_OK,
        )


