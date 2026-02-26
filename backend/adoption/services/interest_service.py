from django.db import transaction, IntegrityError
from adoption.models import Interest, Pet
from adoption.services.notification_service import NotificationService


class InterestService:
    @staticmethod
    def create_interest(user, pet_id):
        """
        Idempotent 'like':
        - If Interest exists, return it.
        - Otherwise create it.
        """
        # Ensure pet exists 404 handled by caller via get_object_or_404 or DoesNotExist
        pet = Pet.objects.get(pet_id=pet_id)

        try:
            with transaction.atomic():
                interest = Interest.objects.create(user=user, pet=pet)
                created = True
                # Non blocking notification
                NotificationService.notify_interest_created(interest)
                return interest, created
        except IntegrityError:
            # Uniqueness constraint (user, pet) ensures dedupe
            return Interest.objects.get(user=user, pet=pet), False

    @staticmethod
    def list_interests(user):
        return (
            Interest.objects
            .select_related("pet", "pet__organization")
            .filter(user=user)
            .order_by("-created_at")
        )
