# FastAPI Routers
from src.routers.auth import router as auth_router
from src.routers.health import router as health_router
from src.routers.organizations import router as organizations_router
from src.routers.users import router as users_router
from src.routers.roles import router as roles_router
from src.routers.executions import router as executions_router
from src.routers.workflows import router as workflows_router
from src.routers.forms import router as forms_router
from src.routers.secrets import router as secrets_router
from src.routers.config import router as config_router
from src.routers.data_providers import router as data_providers_router
from src.routers.websocket import router as websocket_router

__all__ = [
    "auth_router",
    "health_router",
    "organizations_router",
    "users_router",
    "roles_router",
    "executions_router",
    "workflows_router",
    "forms_router",
    "secrets_router",
    "config_router",
    "data_providers_router",
    "websocket_router",
]
