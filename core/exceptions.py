"""
Core exception handling and error mapping 
"""

from __future__ import annotations

from typing import Dict, Any, Optional

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


# ---------------------------------------------------------------------------
# SERVICE-LEVEL EXCEPTIONS
# ---------------------------------------------------------------------------


class ServiceError(Exception):
    """
    Base service exception with structured error information.

    Args:
        code: Error code for identification (e.g., "USER_NOT_FOUND")
        message: Human-readable error message
        details: Additional error details (optional)
        status_code: HTTP status code to map to (optional; fallback code map kullanılacak)
    """

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.status_code = status_code  # None ise code→status map devreye girer
        super().__init__(message)

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"

    def __repr__(self) -> str:
        return (
            f"ServiceError(code='{self.code}', "
            f"message='{self.message}', details={self.details}, "
            f"status_code={self.status_code})"
        )


class BusinessLogicError(ServiceError):
    """Business logic violation error (422)"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


class ValidationError(ServiceError):
    """Data validation error (400)"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotFoundError(ServiceError):
    """Resource not found error (404)"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ConflictError(ServiceError):
    """Resource conflict error (409)"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_409_CONFLICT,
        )


class UnauthorizedError(ServiceError):
    """Authentication required error (401)"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


class ForbiddenError(ServiceError):
    """Authorization failed error (403)"""

    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            code=code,
            message=message,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )


# ---------------------------------------------------------------------------
# PROBLEM DETAILS (RFC 7807)
# ---------------------------------------------------------------------------


def problem_json(
    status_code: int,
    title: str,
    detail: str,
    type_uri: str = "about:blank",
    instance: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create RFC 7807 Problem Details JSON response.

    Örnek:
        {
            "type": "about:blank",
            "title": "Validation Failed",
            "status": 400,
            "detail": "The email field is required",
            "instance": "/api/v1/users",
            "code": "VALIDATION_ERROR",
            "field": "email"
        }
    """
    problem = {
        "type": type_uri,
        "title": title,
        "status": status_code,
        "detail": detail,
    }

    if instance:
        problem["instance"] = instance

    if extra:
        problem.update(extra)

    return problem


# ---------------------------------------------------------------------------
# SERVICE ERROR → HTTPEXCEPTION MAPPING
# ---------------------------------------------------------------------------


# 2. versiyondan gelen code → HTTP status map'i core'da kullanıyoruz :contentReference[oaicite:5]{index=5}
SERVICE_ERROR_STATUS_MAP: Dict[str, int] = {
    # Client errors (4xx)
    "VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
    "INVALID_INPUT": status.HTTP_400_BAD_REQUEST,
    "BAD_REQUEST": status.HTTP_400_BAD_REQUEST,
    "CONSTRAINT_VIOLATION": status.HTTP_400_BAD_REQUEST,
    "DUPLICATE_RESOURCE": status.HTTP_409_CONFLICT,
    "RESOURCE_EXISTS": status.HTTP_409_CONFLICT,
    "UNAUTHORIZED": status.HTTP_401_UNAUTHORIZED,
    "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
    "TOKEN_EXPIRED": status.HTTP_401_UNAUTHORIZED,
    "FORBIDDEN": status.HTTP_403_FORBIDDEN,
    "ACCESS_DENIED": status.HTTP_403_FORBIDDEN,
    "INSUFFICIENT_PERMISSIONS": status.HTTP_403_FORBIDDEN,
    "NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "RESOURCE_NOT_FOUND": status.HTTP_404_NOT_FOUND,
    "METHOD_NOT_ALLOWED": status.HTTP_405_METHOD_NOT_ALLOWED,
    "CONFLICT": status.HTTP_409_CONFLICT,
    "RESOURCE_CONFLICT": status.HTTP_409_CONFLICT,
    "UNPROCESSABLE_ENTITY": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "BUSINESS_RULE_VIOLATION": status.HTTP_422_UNPROCESSABLE_ENTITY,
    "TOO_MANY_REQUESTS": status.HTTP_429_TOO_MANY_REQUESTS,
    "RATE_LIMIT_EXCEEDED": status.HTTP_429_TOO_MANY_REQUESTS,
    # Server errors (5xx)
    "INTERNAL_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "DATABASE_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "EXTERNAL_SERVICE_ERROR": status.HTTP_502_BAD_GATEWAY,
    "SERVICE_UNAVAILABLE": status.HTTP_503_SERVICE_UNAVAILABLE,
}


def _resolve_status_code(error: ServiceError) -> int:
    """
    ServiceError içindeki status_code'u kullanır; yoksa code→status map'ten bulur.
    Hiçbiri yoksa 500 döner.
    """
    if error.status_code is not None:
        return error.status_code

    return SERVICE_ERROR_STATUS_MAP.get(
        error.code,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def map_service_error(
    error: ServiceError,
    instance: Optional[str] = None,
) -> HTTPException:
    """
    ServiceError'ı Problem Details formatında HTTPException'a dönüştürür.

    Route kullanımı:
        try:
            await user_service.create_user(db, data)
        except ServiceError as e:
            raise map_service_error(e, request.url.path)
    """
    http_status = _resolve_status_code(error)

    title_map = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable",
    }
    title = title_map.get(http_status, "Error")

    problem_details = problem_json(
        status_code=http_status,
        title=title,
        detail=error.message,
        type_uri=f"https://httpstatuses.com/{http_status}",
        instance=instance,
        extra={
            "code": error.code,
            **(error.details or {}),
        },
    )

    return HTTPException(
        status_code=http_status,
        detail=problem_details,
        headers={"Content-Type": "application/problem+json"},
    )


def map_service_error_to_response(
    error: ServiceError,
    instance: Optional[str] = None,
) -> JSONResponse:
    """
    ServiceError'ı direkt JSONResponse olarak döner.
    Eğer HTTPException yerine Response dönmek istersen kullanabilirsin.
    """
    http_exc = map_service_error(error, instance=instance)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
        headers=http_exc.headers or {"Content-Type": "application/problem+json"},
    )


# ---------------------------------------------------------------------------
# GENERIC FACTORY'LER (NO-CODE ORTAK)
# ---------------------------------------------------------------------------


class CommonServiceErrors:
    """
    Proje-agnostic (domain bağımsız) sık kullanılan ServiceError factory'leri.

    Domain'e özel olanlar (user_not_found, project_not_found vs.) için
    ilgili proje paketinde yeni factory'ler oluşturman daha mantıklı.
    """

    @staticmethod
    def not_found(resource: str, identifier: Optional[str] = None) -> NotFoundError:
        detail = f"{resource} not found"
        if identifier:
            detail += f" with identifier: {identifier}"

        return NotFoundError(
            code="RESOURCE_NOT_FOUND",
            message=detail,
            details={"resource": resource, "identifier": identifier},
        )

    @staticmethod
    def already_exists(
        resource: str,
        identifier: Optional[str] = None,
    ) -> ConflictError:
        detail = f"{resource} already exists"
        if identifier:
            detail += f" with identifier: {identifier}"

        return ConflictError(
            code="RESOURCE_EXISTS",
            message=detail,
            details={"resource": resource, "identifier": identifier},
        )

    @staticmethod
    def validation_error(field: str, message: str) -> ValidationError:
        return ValidationError(
            code="VALIDATION_ERROR",
            message=f"Validation failed for {field}: {message}",
            details={"field": field, "validation_message": message},
        )

    @staticmethod
    def forbidden(action: str, resource: Optional[str] = None) -> ForbiddenError:
        detail = f"Access denied for action: {action}"
        if resource:
            detail += f" on resource: {resource}"

        return ForbiddenError(
            code="ACCESS_DENIED",
            message=detail,
            details={"action": action, "resource": resource},
        )

    @staticmethod
    def business_rule_violation(
        rule: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> BusinessLogicError:
        return BusinessLogicError(
            code="BUSINESS_RULE_VIOLATION",
            message=f"Business rule violation: {rule}",
            details={"rule": rule, **(details or {})},
        )


# ---------------------------------------------------------------------------
# DECORATOR: ROUTE'LARDA OTOMATİK HANDLE
# ---------------------------------------------------------------------------


def handle_service_errors(func):
    """
    Decorator to automatically handle ServiceError in route functions.

    Usage:
        @router.get("/users/{user_id}")
        @handle_service_errors
        async def get_user(user_id: str, db: AsyncSession = Depends(get_db)):
            return await user_service.get_user_by_id(db, user_id)
    """
    import functools
    from fastapi import Request

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        request: Optional[Request] = None

        # Request nesnesini bulmaya çalış
        for arg in args:
            if isinstance(arg, Request):
                request = arg
                break

        if request is None:
            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break

        try:
            return await func(*args, **kwargs)
        except ServiceError as e:
            instance = request.url.path if request else None
            raise map_service_error(e, instance)

    return wrapper
