import logging
from django.conf import settings
from adoption.models import Interest, Application
from django.utils import timezone

logger = logging.getLogger(__name__)

class NotificationService:
    """
    v0 stub.
    For MVP: "send" means log a payload and mark notification_status.
    Must never raise to caller; failures should be recorded.
    """

    @staticmethod
    def notify_interest_created(interest: Interest) -> None:
        try:
            if not getattr(settings, "WOOFER_NOTIFICATIONS_ENABLED", True):
                return
            
            if getattr(settings, "WOOFER_NOTIFICATIONS_FORCE_FAIL", False):
                raise RuntimeError("Forced notification failure (test)")
            pet = interest.pet
            org = pet.organization
            user = interest.user

            payload = {
                "type": "INTEREST_CREATED",
                "interest_id": str(interest.interest_id),
                "pet_id": str(pet.pet_id),
                "pet_name": pet.name,
                "organization_id": str(org.organization_id),
                "organization_name": org.name,
                "organization_contact_email": org.contact_email,
                "user_id": str(user.id),
                "username": getattr(user, "username", None),
                "user_email": getattr(user, "email", None),
            }

            logger.info("WooferNotificationStub %s", payload)

            Interest.objects.filter(pk=interest.pk).update(
                notification_status=Interest.NotificationStatus.SENT,
                notification_attempted_at=timezone.now(),
            )
        except Exception as e:
            logger.exception("Notification stub failed for interest_id=%s", interest.interest_id)
            Interest.objects.filter(pk=interest.pk).update(
                notification_status=Interest.NotificationStatus.FAILED,
                notification_attempted_at=timezone.now(),
            )
            return
        
    @staticmethod
    def notify_application_created(app: Application) -> None:
        try:
            if getattr(settings, "WOOFER_NOTIFICATIONS_FORCE_FAIL", False):
                raise RuntimeError("Forced notification failure (test)")

            pet = app.pet
            org = pet.organization
            user = app.user

            payload = {
                "type": "APPLICATION_CREATED",
                "application_id": str(app.application_id),
                "pet_id": str(pet.pet_id),
                "pet_name": pet.name,
                "organization_id": str(org.organization_id),
                "organization_name": org.name,
                "organization_contact_email": org.contact_email,
                "user_id": str(user.id),
                "username": getattr(user, "username", None),
                "user_email": getattr(user, "email", None),
                "apply_url": getattr(pet, "apply_url", None),
                "apply_hint": getattr(pet, "apply_hint", None),
                "payload": app.payload,
            }

            logger.info("WooferApplicationEmailStub %s", payload)

            app.email_status = Application.EmailStatus.SENT
            app.save(update_fields=["email_status"])

        except Exception:
            logger.exception(
                "Application notification failed for application_id=%s",
                app.application_id,
            )
            app.email_status = Application.EmailStatus.FAILED
            app.save(update_fields=["email_status"])
            return
