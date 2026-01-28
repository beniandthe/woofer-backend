from adoption.models import Pet

class PetService:
    @staticmethod
    def get_pet_detail(pet_id):
        # Select related organization for one-query detail fetch
        return Pet.objects.select_related("organization").get(pet_id=pet_id)
