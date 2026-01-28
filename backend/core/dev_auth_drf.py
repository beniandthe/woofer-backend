from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication

class DevHeaderAuthentication(BaseAuthentication):
    """
    DEV ONLY.
    When DEBUG and WOOFER_DEV_AUTH is True, authenticate via:
      X-Woofer-Dev-User: <username>
    """
    def authenticate(self, request):
        if not (getattr(settings, "WOOFER_DEV_AUTH", False) and settings.DEBUG):
            return None

        username = request.headers.get("X-Woofer-Dev-User")
        if not username:
            return None

        User = get_user_model()
        user, _ = User.objects.get_or_create(username=username)
        return (user, None)
