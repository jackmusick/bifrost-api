"""Contract-level tests for Solution DTOs.

scope is DERIVED from organization_id (NULL == global), not stored on the ORM —
so a global install must serialize scope='global', not the field default
(Codex P2 fix).
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src.models.contracts.solutions import (
    Solution as SolutionDTO,
    SolutionSdkUpdateBatchRequest,
    SolutionSdkUpdateBatchResponse,
)


def _row(org_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        slug="s",
        name="S",
        organization_id=org_id,
        global_repo_access=False,
        git_connected=False,
        git_repo_url=None,
    )


def test_global_install_serializes_scope_global() -> None:
    dto = SolutionDTO.model_validate(_row(None))
    assert dto.scope == "global"
    assert dto.model_dump()["scope"] == "global"


def test_org_install_serializes_scope_org() -> None:
    dto = SolutionDTO.model_validate(_row(uuid.uuid4()))
    assert dto.scope == "org"
    assert dto.model_dump()["scope"] == "org"


def test_solution_sdk_aggregate_fields_default_not_applicable() -> None:
    dto = SolutionDTO.model_validate(_row(uuid.uuid4()))

    assert dto.sdk_status == "not_applicable"
    assert dto.sdk_actionable_count == 0


def test_solution_sdk_update_batch_request_requires_explicit_solution_ids() -> None:
    solution_id = uuid.uuid4()

    request = SolutionSdkUpdateBatchRequest(solution_ids=[solution_id])

    assert request.solution_ids == [solution_id]
    with pytest.raises(ValidationError):
        SolutionSdkUpdateBatchRequest(solution_ids=[])


def test_solution_sdk_update_batch_response_contains_per_app_results() -> None:
    accepted_app_id = uuid.uuid4()
    skipped_app_id = uuid.uuid4()
    job_id = uuid.uuid4()

    response = SolutionSdkUpdateBatchResponse(
        accepted=[
            {
                "application_id": accepted_app_id,
                "job_id": job_id,
                "status": "queued",
                "reused": False,
                "notification_id": None,
            }
        ],
        skipped=[
            {
                "application_id": skipped_app_id,
                "reason": "current",
            }
        ],
    )

    assert response.accepted[0].application_id == accepted_app_id
    assert response.accepted[0].job_id == job_id
    assert response.skipped[0].application_id == skipped_app_id
    assert response.skipped[0].reason == "current"
