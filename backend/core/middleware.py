import uuid
from datetime import datetime, timezone

class RequestContextMiddleware:
    """
    Attaches request_id and timestamp to each request.
    request.request_id: uuid string
    request.request_timestamp: ISO8601 string
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = str(uuid.uuid4())
        request.request_timestamp = datetime.now(timezone.utc).isoformat()
        response = self.get_response(request)
        return response
