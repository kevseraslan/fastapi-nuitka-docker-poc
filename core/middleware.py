"""
Core middleware and logging utilities
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Iterable, List, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

# Ana logger
logger = logging.getLogger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


# ---------------------------------------------------------------------------
# REQUEST ID MIDDLEWARE
# ---------------------------------------------------------------------------


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Her istek için benzersiz bir Request ID üretir veya mevcut header'dan alır.

    - request.state.request_id içine yazar
    - Response header'ına X-Request-ID ekler
    """

    def __init__(self, app: FastAPI, header_name: str = REQUEST_ID_HEADER) -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        # Var olan ID'yi kullan, yoksa yeni üret
        request_id = request.headers.get(self.header_name)
        if not request_id:
            request_id = str(uuid.uuid4())

        # Request state'e ekle
        request.state.request_id = request_id

        # Devam et
        response: Response = await call_next(request)

        # Response header'a ekle
        response.headers[self.header_name] = request_id
        return response


# ---------------------------------------------------------------------------
# ACCESS LOG MIDDLEWARE
# ---------------------------------------------------------------------------


SENSITIVE_HEADERS = {"authorization", "cookie", "x-api-key", "x-access-token"}


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Her HTTP isteği için access log üretir.

    Log içeriği:
    - method, path, query, status_code
    - duration_ms
    - client_ip, user_agent
    - request_id
    """

    def __init__(self, app: FastAPI) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()

        # Request ID (RequestIDMiddleware yoksa bile fallback üretelim)
        request_id = getattr(request.state, "request_id", None) or str(uuid.uuid4())
        request.state.request_id = request_id

        # Temel request bilgileri
        method = request.method
        path = request.url.path
        query = request.url.query
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "-")

        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "query": query,
                    "status_code": 500,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": client_ip,
                    "user_agent": user_agent,
                },
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000

        extra = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "query": query,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
            "client_ip": client_ip,
            "user_agent": user_agent,
        }

        logger.info(
            "%s %s %s %d %.2fms",
            method,
            path,
            f"?{query}" if query else "",
            response.status_code,
            duration_ms,
            extra=extra,
        )

        # Response'a content-length yoksa ekleyebiliriz
        if "content-length" not in response.headers:
            body_length = len(getattr(response, "body", b"") or b"")
            response.headers["Content-Length"] = str(body_length)

        return response


# ---------------------------------------------------------------------------
# SECURITY HEADERS MIDDLEWARE
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Temel güvenlik header'larını ekler.

    Not:
    - /docs ve /redoc path'leri için Swagger UI ile uyumlu olacak şekilde
      Content-Security-Policy'yi biraz yumuşatmak isteyebilirsin.
    - İstersen init parametrelerini genişletebilirsin.
    """

    def __init__(
        self,
        app: FastAPI,
        enable_hsts: bool = False,
        allow_iframe_paths: Optional[Iterable[str]] = None,
    ) -> None:
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.allow_iframe_paths = set(allow_iframe_paths or [])

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)

        # X-Content-Type-Options
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        # X-XSS-Protection (modern tarayıcılarda çok etkili değil ama zararı yok)
        response.headers.setdefault("X-XSS-Protection", "1; mode=block")
        # Referrer-Policy
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

        # X-Frame-Options
        path = request.url.path
        if any(path.startswith(p) for p in self.allow_iframe_paths):
            # Bu path'ler iframe'e izinli (örneğin /uploads/pdf gibi)
            pass
        else:
            response.headers.setdefault("X-Frame-Options", "DENY")

        # Content-Security-Policy (basit, generic bir CSP)
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "img-src 'self' data:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; "
            "font-src 'self'; ",
        )

        # Strict-Transport-Security (HSTS) - sadece HTTPS için mantıklı
        if self.enable_hsts and request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=63072000; includeSubDomains; preload",
            )

        return response


# ---------------------------------------------------------------------------
# CORS SETUP
# ---------------------------------------------------------------------------


def setup_cors(app: FastAPI, origins: List[str]) -> None:
    """
    CORS ayarlarını yapar.

    origins: İzin verilen origin listesi
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )


# ---------------------------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------------------------


def configure_logging(debug: bool = False) -> None:
    """
    Uygulama genel logging ayarlarını yapar.

    - debug=True iken daha detaylı log
    - debug=False iken INFO seviye ve bazı gürültülü logger'lar kısılır
    """
    level = logging.DEBUG if debug else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    )

    # Uvicorn ve benzeri logger'ları ayarla
    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO if debug else logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(level)

    # SQLAlchemy çok gürültülü olabiliyor
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if debug else logging.WARNING)


# ---------------------------------------------------------------------------
# HELPER FONKSİYONLAR
# ---------------------------------------------------------------------------


def get_request_id(request: Request) -> Optional[str]:
    """
    RequestIDMiddleware tarafından set edilen request_id'yi döner.
    """
    return getattr(request.state, "request_id", None)


def log_business_event(
    request: Request,
    event: str,
    details: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
) -> None:
    """
    İş mantığına ait önemli event'leri loglamak için helper.

    Örnek:
        log_business_event(request, "USER_SIGNUP", {"user_id": user.id})
    """
    request_id = get_request_id(request)
    client_ip = request.client.host if request.client else None

    logger.log(
        level,
        "BusinessEvent %s",
        event,
        extra={
            "request_id": request_id,
            "event": event,
            "details": details or {},
            "client_ip": client_ip,
            "path": request.url.path,
            "method": request.method,
        },
    )


# ---------------------------------------------------------------------------
# MIDDLEWARE SETUP ENTRYPOINT
# ---------------------------------------------------------------------------


def setup_middleware(
    app: FastAPI,
    cors_origins: Optional[List[str]] = None,
    enable_access_log: bool = True,
    enable_security_headers: bool = True,
    enable_hsts: bool = False,
    allow_iframe_paths: Optional[Iterable[str]] = None,
) -> None:
    """
    Uygulamanın tüm core middleware'lerini tek noktadan ekler.

    Önerilen çağrı:
        app = FastAPI(...)
        configure_logging(debug=settings.debug)
        setup_middleware(app, cors_origins=settings.cors_origins)
    """
    # Güvenlik header'ları
    if enable_security_headers:
        app.add_middleware(
            SecurityHeadersMiddleware,
            enable_hsts=enable_hsts,
            allow_iframe_paths=allow_iframe_paths or [],
        )

    # Access log
    if enable_access_log:
        app.add_middleware(AccessLogMiddleware)

    # Request ID
    app.add_middleware(RequestIDMiddleware)

    # CORS
    setup_cors(app, cors_origins or [])
