import uuid
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code


class ForbiddenError(APIError):
    def __init__(self, message: str = "Access denied"):
        super().__init__("FORBIDDEN", message, 403)


class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__("NOT_FOUND", message, 404)


class ConflictError(APIError):
    def __init__(self, message: str = "Conflict"):
        super().__init__("CONFLICT", message, 409)


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__("UNAUTHORIZED", message, 401)


def error_response(code: str, message: str, request_id: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "requestId": request_id}},
    )


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        try:
            return await call_next(request)
        except APIError as e:
            return error_response(e.code, e.message, request_id, e.status_code)
        except Exception as e:
            return error_response("INTERNAL_ERROR", str(e), request_id, 500)
