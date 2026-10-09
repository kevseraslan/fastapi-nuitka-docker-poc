"""
Core package init 
"""

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------
from .settings import Settings, settings

# ---------------------------------------------------------------------------
# EXCEPTIONS
# ---------------------------------------------------------------------------
from .exceptions import (
    # temel service exception sınıfları
    ServiceError,
    BusinessLogicError,
    ValidationError,
    NotFoundError,
    ConflictError,
    UnauthorizedError,
    ForbiddenError,
    # RFC 7807 problem details
    problem_json,
    map_service_error,
    map_service_error_to_response,
    # generic factory'ler
    CommonServiceErrors,
    # decorator
    handle_service_errors,
)

# ---------------------------------------------------------------------------
# MIDDLEWARE & LOGGING
# ---------------------------------------------------------------------------
from .middleware import (
    # logging config
    configure_logging,
    # middleware setup
    setup_middleware,
    setup_cors,
    # middleware sınıfları
    RequestIDMiddleware,
    AccessLogMiddleware,
    SecurityHeadersMiddleware,
    # helper'lar
    REQUEST_ID_HEADER,
    get_request_id,
    log_business_event,
)

# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

__all__ = [
    # settings
    "Settings",
    "settings",

    # exceptions
    "ServiceError",
    "BusinessLogicError",
    "ValidationError",
    "NotFoundError",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "problem_json",
    "map_service_error",
    "map_service_error_to_response",
    "CommonServiceErrors",
    "handle_service_errors",

    # middleware & logging
    "configure_logging",
    "setup_middleware",
    "setup_cors",
    "RequestIDMiddleware",
    "AccessLogMiddleware",
    "SecurityHeadersMiddleware",
    "REQUEST_ID_HEADER",
    "get_request_id",
    "log_business_event",
]
