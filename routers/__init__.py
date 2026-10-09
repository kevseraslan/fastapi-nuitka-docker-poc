from .dashboard import router as dashboard_router
from .login import router as login_router
from .logout import router as logout_router
from .register import router as register_router

__all__ = [
    "dashboard_router",
    "login_router",
    "logout_router",
    "register_router",
]