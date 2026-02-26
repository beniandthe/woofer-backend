from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework import status as drf_status


def canonical_exception_handler(exc, context):
    """
    Ensures all API errors match:
    {
      ok: false,
      error: { code, message, details },
      request_id,
      timestamp
    }
    """
    response = drf_exception_handler(exc, context)
    request = context.get("request")

    request_id = getattr(request, "request_id", None)
    timestamp = getattr(request, "request_timestamp", None)

    if response is None:
        # Non DRF exception
        return None

    code = "API_ERROR"
    message = "Request failed."
    details = response.data if isinstance(response.data, (dict, list)) else {}

    # DRF sometimes provides "detail"
    if isinstance(response.data, dict) and "detail" in response.data:
        message = str(response.data.get("detail"))

    # Add more specific codes for common statuses
    if response.status_code == drf_status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHORIZED"
        message = "Unauthorized."
    elif response.status_code == drf_status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
        message = "Forbidden."
    elif response.status_code == drf_status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"
        message = "Not found."
    elif response.status_code == drf_status.HTTP_400_BAD_REQUEST:
        code = "BAD_REQUEST"
        message = "Bad request."

    response.data = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "request_id": request_id,
        "timestamp": timestamp,
    }
    return response
