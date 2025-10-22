"""
Repository pattern for database access
Centralizes all TableStorage operations and provides type-safe, indexed queries
"""

from .audit import AuditRepository
from .base import BaseRepository
from .config import ConfigRepository
from .executions import ExecutionRepository
from .forms import FormRepository
from .oauth import OAuthRepository
from .organizations import OrganizationRepository
from .roles import RoleRepository
from .scoped_repository import ScopedRepository
from .users import UserRepository

__all__ = [
    "AuditRepository",
    "BaseRepository",
    "ScopedRepository",
    "ExecutionRepository",
    "FormRepository",
    "OrganizationRepository",
    "UserRepository",
    "RoleRepository",
    "OAuthRepository",
    "ConfigRepository",
]
