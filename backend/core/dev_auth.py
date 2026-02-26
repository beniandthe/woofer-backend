from django.conf import settings
from django.contrib.auth import get_user_model
from core.dev_auth_flags import dev_header_auth_enabled

class DevHeaderAuthMiddleware:
    """
    DEV ONLY.
    If DEBUG and WOOFER_DEV_AUTH=1, allow setting request.user via header:
      X-Woofer-Dev-User: <username>

    This is only for local web smoke tests before real auth is integrated.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if dev_header_auth_enabled():
            username = request.headers.get("X-Woofer-Dev-User")
            if username:
                User = get_user_model()
                user, _ = User.objects.get_or_create(username=username)
                request.user = user
        return self.get_response(request)
