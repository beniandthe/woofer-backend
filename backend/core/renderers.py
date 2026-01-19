from rest_framework.renderers import JSONRenderer
from rest_framework.utils.serializer_helpers import ReturnDict, ReturnList

class EnvelopeJSONRenderer(JSONRenderer):
    """
    Wrap all successful API responses in the canonical envelope.
    Errors are handled by a custom exception handler.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # If renderer_context is missing, fallback to default behavior
        if renderer_context is None:
            return super().render(data, accepted_media_type, renderer_context)

        response = renderer_context.get("response")
        request = renderer_context.get("request")

        # If DRF is already returning an error envelope, do not double-wrap
        if isinstance(data, dict) and data.get("ok") in (True, False) and ("data" in data or "error" in data):
            return super().render(data, accepted_media_type, renderer_context)

        request_id = getattr(request, "request_id", None)
        timestamp = getattr(request, "request_timestamp", None)

        status_code = getattr(response, "status_code", 200)
        is_error = status_code >= 400

        # Success paths only; errors will be formatted by exception handler
        if not is_error:
            envelope = {
                "ok": True,
                "data": data if data is not None else {},
                "meta": {},
                "request_id": request_id,
                "timestamp": timestamp,
            }
            return super().render(envelope, accepted_media_type, renderer_context)

        # For safety: if an error leaks here, still wrap minimally
        envelope = {
            "ok": False,
            "error": {
                "code": "UNHANDLED_ERROR",
                "message": "An error occurred.",
                "details": data if isinstance(data, (dict, ReturnDict, ReturnList)) else {},
            },
            "request_id": request_id,
            "timestamp": timestamp,
        }
        return super().render(envelope, accepted_media_type, renderer_context)
