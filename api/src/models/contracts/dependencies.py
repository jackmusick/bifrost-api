"""Dependency graph API contracts."""

from uuid import UUID

from pydantic import BaseModel, Field


class DependencyAvailabilityRequest(BaseModel):
    """Entity IDs to check for dependency graph relationships."""

    workflow_ids: list[UUID] = Field(default_factory=list)
    form_ids: list[UUID] = Field(default_factory=list)
    app_ids: list[UUID] = Field(default_factory=list)
    agent_ids: list[UUID] = Field(default_factory=list)


class DependencyAvailabilityResponse(BaseModel):
    """Relationship availability keyed by composite entity ID."""

    has_relationships: dict[str, bool] = Field(default_factory=dict)
