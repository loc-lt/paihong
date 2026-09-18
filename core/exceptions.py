from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler


class RevisionConflict(ValidationError):
    """Optimistic concurrency mismatch on base_revision_id — maps to HTTP 409."""


def custom_exception_handler(exc, context):
    if isinstance(exc, RevisionConflict):
        from core.responses import revision_conflict_response

        return revision_conflict_response(exc)

    response = exception_handler(exc, context)

    error_messages = {
        status.HTTP_401_UNAUTHORIZED: {
            "status": False,
            "message": _("Authentication credentials were not provided."),
        },
        status.HTTP_403_FORBIDDEN: {
            "status": False,
            "message": "Unfortunately, you do not have permission.",
        },
        status.HTTP_404_NOT_FOUND: {
            "status": False,
            "message": "The requested resource could not be found.",
        },
    }

    if response is not None and response.status_code in error_messages:
        payload = dict(error_messages[response.status_code])
        if response.status_code == status.HTTP_401_UNAUTHORIZED and getattr(
            exc, "detail", None
        ):
            detail = exc.detail
            if isinstance(detail, (list, tuple)):
                detail = detail[0]
            payload["message"] = str(detail)
        return Response(payload, status=response.status_code)

    # DRF does not convert unhandled exceptions into a Response, so a 500
    # mapping in error_messages would never run. Handle that case in production.
    if response is None and not settings.DEBUG:
        return Response(
            {
                "status": False,
                "message": "An unexpected error occurred on the server.",
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response
