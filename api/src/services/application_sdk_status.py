from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Protocol
from uuid import UUID

from shared.version import get_version
from src.services.sdk_package import sdk_contract_version, sdk_fingerprint

ApplicationSdkStatus = Literal[
    "not_applicable",
    "unknown",
    "current",
    "update_available",
    "update_required",
]


@dataclass(frozen=True)
class CurrentApplicationSdkMetadata:
    package_version: str
    fingerprint: str | None
    contract_version: int


class ApplicationSdkStatusInput(Protocol):
    app_model: str
    solution_id: UUID | None
    active_deployment_id: UUID | None
    sdk_fingerprint: str | None
    sdk_built_at: object | None


@lru_cache(maxsize=1)
def current_sdk_metadata() -> CurrentApplicationSdkMetadata:
    version = get_version()
    return CurrentApplicationSdkMetadata(
        package_version=version,
        fingerprint=sdk_fingerprint(version),
        contract_version=sdk_contract_version(),
    )


def application_sdk_status(
    application: ApplicationSdkStatusInput,
    current: CurrentApplicationSdkMetadata,
) -> ApplicationSdkStatus:
    if application.app_model == "inline_v1":
        return "not_applicable"
    if (
        not application.sdk_fingerprint
        or application.sdk_built_at is None
        or not current.fingerprint
    ):
        return "unknown"
    if application.sdk_fingerprint == current.fingerprint:
        return "current"
    return "update_available"


def sdk_source_available(application: ApplicationSdkStatusInput) -> bool:
    if application.app_model == "inline_v1":
        return False
    if application.solution_id is not None:
        return True
    return (
        application.active_deployment_id is not None
        and application.sdk_built_at is not None
    )
