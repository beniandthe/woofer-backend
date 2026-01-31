from .base import *  # noqa
import os


WOOFER_NOTIFICATIONS_FORCE_FAIL = os.getenv("WOOFER_NOTIFICATIONS_FORCE_FAIL") == "1"

DEBUG = True
WOOFER_DEV_AUTH = True

# Insert middleware early so DRF sees request.user set
MIDDLEWARE.insert(1, "core.dev_auth.DevHeaderAuthMiddleware")

REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = [
    "core.renderers.EnvelopeJSONRenderer",
    "rest_framework.renderers.BrowsableAPIRenderer",
]

REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] = [
    "core.dev_auth_drf.DevHeaderAuthentication",
] + list(REST_FRAMEWORK.get("DEFAULT_AUTHENTICATION_CLASSES", []))
