from typing import Any


def build_success(
    data: Any = None,
    message: str = "ok",
    code: int = 0,
    request_id: str | None = None,
) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": request_id,
    }


def build_error(
    message: str,
    code: int,
    request_id: str | None = None,
    details: Any = None,
) -> dict:
    payload = {
        "code": code,
        "message": message,
        "data": None,
        "request_id": request_id,
    }
    if details is not None:
        payload["details"] = details
    return payload
