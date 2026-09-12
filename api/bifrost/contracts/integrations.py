"""Minimal CLI-side mirror of integration create/update DTOs."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ConfigItemType = Literal["string", "int", "bool", "json", "secret"]


class ConfigSchemaItem(BaseModel):
    """Metadata for a single configuration item (CLI mirror)."""

    model_config = ConfigDict(from_attributes=True)

    key: str = Field(min_length=1, max_length=255, pattern=r"^[a-zA-Z0-9_]+$")
    type: ConfigItemType
    required: bool = Field(default=False)
    description: str | None = Field(default=None, max_length=500)
    options: list[str] | None = Field(default=None)


class IntegrationCreate(BaseModel):
    """Request model for creating an integration (CLI mirror)."""

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    config_schema: list[ConfigSchemaItem] | None = Field(default=None)
    entity_id: str | None = Field(default=None, min_length=1, max_length=255)
    entity_id_name: str | None = Field(default=None, max_length=255)
    default_entity_id: str | None = Field(default=None, max_length=255)


class IntegrationUpdate(BaseModel):
    """Request model for updating an integration (CLI mirror)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    list_entities_data_provider_id: UUID | None = Field(default=None)
    config_schema: list[ConfigSchemaItem] | None = Field(default=None)
    entity_id: str | None = Field(default=None, min_length=1, max_length=255)
    entity_id_name: str | None = Field(default=None, max_length=255)
    default_entity_id: str | None = Field(default=None, max_length=255)


class IntegrationMappingCreate(BaseModel):
    """Request model for creating an integration mapping (CLI mirror)."""

    organization_id: UUID
    entity_id: str = Field(min_length=1, max_length=255)
    entity_name: str | None = Field(default=None, max_length=255)
    oauth_token_id: UUID | None = Field(default=None)
    config: dict[str, Any] | None = Field(default=None)


class IntegrationMappingUpdate(BaseModel):
    """Request model for updating an integration mapping (CLI mirror)."""

    entity_id: str | None = Field(default=None, min_length=1, max_length=255)
    entity_name: str | None = Field(default=None, max_length=255)
    oauth_token_id: UUID | None = Field(default=None)
    config: dict[str, Any] | None = Field(default=None)
