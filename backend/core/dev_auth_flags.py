from django.conf import settings

def dev_header_auth_enabled() -> bool:
    """
    Single source of truth for whether dev header auth is allowed.

    Requirements:
    - DEBUG must be True
    - WOOFER_DEV_AUTH must be True (enabled by dev settings)
    - WOOFER_ALLOW_DEV_AUTH must be explicitly enabled via env (default OFF)
    """
    return bool(
        getattr(settings, "DEBUG", False)
        and getattr(settings, "WOOFER_DEV_AUTH", False)
        and getattr(settings, "WOOFER_ALLOW_DEV_AUTH", False)
    )