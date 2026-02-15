from django.db import transaction, IntegrityError
from rest_framework.exceptions import ValidationError, NotFound

from adoption.models import Application, Pet
from adoption.services.notification_service import NotificationService
from adoption.services.user_profile_service import UserProfileService
from adoption.services.handoff_payload_builder import HandoffPayloadBuilder


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

        # Profile snapshot at apply-time
        profile = UserProfileService.get_or_create_profile(user)
        profile_snapshot = {
            "home_type": profile.home_type,
            "has_kids": profile.has_kids,
            "has_dogs": profile.has_dogs,
            "has_cats": profile.has_cats,
            "activity_level": profile.activity_level,
            "experience_level": profile.experience_level,
            "preferences": profile.preferences or {},
            "home_postal_code": getattr(profile, "home_postal_code", "") or "",
        }

        handoff_payload = HandoffPayloadBuilder.build(
            pet=pet,
            organization=pet.organization,
            profile=profile,
            user=user,
        )

        # Create (idempotent) inside transaction
        try:
            with transaction.atomic():
                app = Application.objects.create(
                    user=user,
                    pet=pet,
                    organization=pet.organization,
                    payload=payload or {},
                    profile_snapshot=profile_snapshot,
                    handoff_payload=handoff_payload,
                )
        except IntegrityError:
            app = Application.objects.get(user=user, pet=pet)

        # IMPORTANT: notify AFTER transaction so side-effects aren't tied to rollback
        NotificationService.notify_application_created(app)
        return app

