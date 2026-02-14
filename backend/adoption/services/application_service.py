from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError, NotFound

from adoption.models import Application, Pet
from adoption.services.notification_service import NotificationService


class ApplicationService:
    @staticmethod
    def create_application(user, pet_id, payload: dict, organization_id=None) -> Application:
        try:
            pet = Pet.objects.select_related("organization").get(pet_id=pet_id)
        except Pet.DoesNotExist:
            raise NotFound("Pet not found")

        # Optional safety check (keeps your mismatch test valid)
        if organization_id is not None:
            if str(pet.organization.organization_id) != str(organization_id):
                raise ValidationError({"organization_id": ["does not match pet.organization"]})

        # Create (idempotent) inside transaction
        try:
            with transaction.atomic():
                app = Application.objects.create(
                    user=user,
                    pet=pet,
                    organization=pet.organization,
                    payload=payload or {},
                )
        except IntegrityError:
            app = Application.objects.get(user=user, pet=pet)

        # IMPORTANT: notify AFTER transaction so side-effects aren't tied to rollback
        NotificationService.notify_application_created(app)
        return app

