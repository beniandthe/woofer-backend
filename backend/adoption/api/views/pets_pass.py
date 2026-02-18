from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from adoption.services.pet_seen_service import PetSeenService
from rest_framework.response import Response



class PetPassView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pet_id: str):
        seen, created = PetSeenService.mark_seen(request.user, pet_id)
        return Response(
                {
                    "pet_id": str(seen.pet.pet_id),
                    "status": "PASSED",
                    "created": created,
                },
            status=status.HTTP_200_OK,
            )
            

