from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError
from adoption.models import Application, Pet, Organization

class ApplicationService:
    @staticmethod
    def create_application(user, pet_id, organization_id, payload: dict):
        """
        Lean MVP:
        - Create a handoff record for a given (user, pet).
        - Idempotent: returns existing application if unique constraint hits.
        - Validates pet exists and organization matches pet.organization.
        """
        pet = Pet.objects.select_related("organization").get(pet_id=pet_id)
        if str(pet.organization.organization_id) != str(organization_id):
            raise ValidationError({
                "organization_id": "Organization does not match the pet's organization."
            })

        # Ensure org exists (should, but keep explicit)
        organization = Organization.objects.get(organization_id=organization_id)

        try:
            with transaction.atomic():
                app = Application.objects.create(
                    user=user,
                    pet=pet,
                    organization=organization,
                    payload=payload or {},
                )
                return app
        except IntegrityError:
            # Unique (user, pet) constraint
            return Application.objects.get(user=user, pet=pet)
