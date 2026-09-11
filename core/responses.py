from rest_framework import status
from rest_framework.response import Response


def success_response(data, message, http_status=status.HTTP_200_OK):
    return Response(
        {"status": True, "data": data, "message": message},
        status=http_status,
    )


def revision_conflict_response(error):
    message = error.detail
    if isinstance(message, dict):
        message = next(iter(message.values()))
        if isinstance(message, list):
            message = message[0]
    return Response(
        {"status": False, "message": message},
        status=status.HTTP_409_CONFLICT,
    )
