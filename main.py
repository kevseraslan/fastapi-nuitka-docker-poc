import os
import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from starlette.staticfiles import StaticFiles

# Core imports
from core.settings import Settings
from core.exceptions import ServiceError, map_service_error_to_response
from core.middleware import configure_logging, setup_middleware, get_request_id
from core.settings import init_settings

init_settings()  #  Load env variables
# ==========================
# Router imports (AUTO-GENERATED)
from routers import dashboard
from routers import login
from routers import logout
from routers import register
# ==========================


def create_app() -> FastAPI:
    settings = Settings()

    # Configure logging
    configure_logging(settings.debug)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Auto-generated backend for Proje 27/01 16:15",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # --- Exception Handlers ---
    @app.exception_handler(ServiceError)
    async def service_error_exception_handler(request: Request, exc: ServiceError):
        return map_service_error_to_response(exc)

    @app.exception_handler(ValueError)
    async def value_error_exception_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"status": "error", "message": f"Invalid data: {exc}"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"status": "error", "message": "Internal Server Error"},
        )

    # --- Middleware ---
    setup_middleware(
        app,
        cors_origins=settings.cors_origins,
        enable_security_headers=False,
    )

    # --- Static uploads ---
    uploads_dir = "uploads"
    if os.path.exists(uploads_dir) and os.path.isdir(uploads_dir):
        app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

    # --- Router includes (AUTO-GENERATED) ---
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(login.router, prefix="/api")
    app.include_router(logout.router, prefix="/api")
    app.include_router(register.router, prefix="/api")

    # --- Basic Endpoints ---
    @app.get("/")
    async def root():
        return {"message": "Backend OK"}

    @app.get("/health")
    async def health(request: Request):
        return {"status": "healthy", "request_id": get_request_id(request)}

    return app


app = create_app()

if __name__ == "__main__":
    s = Settings()
    uvicorn.run("main:app", host=s.host, port=s.port, reload=s.debug)
