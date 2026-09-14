from rest_framework.views import exception_handler as drf_exception_handler


def custom_exception_handler(exc, context):
    """Wraps DRF's default error body in a stable {"error": {...}} envelope
    so API consumers can rely on one shape for 4xx/5xx responses regardless
    of which view or exception produced them."""
    response = drf_exception_handler(exc, context)
    if response is not None:
        response.data = {
            "error": {
                "status_code": response.status_code,
                "detail": response.data,
            }
        }
    return response
