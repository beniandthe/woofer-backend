from django.db import IntegrityError, transaction
from adoption.models import Pet, PetSeen


class PetSeenService:
    @staticmethod
    def mark_seen(user, pet_id):
        # Ensure pet exists
        pet = Pet.objects.get(pet_id=pet_id)

        try:
            with transaction.atomic():
                obj = PetSeen.objects.create(user=user, pet=pet)
                created = True
        except IntegrityError:
            obj = PetSeen.objects.get(user=user, pet=pet)
            created = False

        return obj, created
