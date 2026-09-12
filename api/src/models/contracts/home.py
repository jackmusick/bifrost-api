"""Authenticated Home launcher contracts. No embedded or portable resource grants."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HomeResource(BaseModel):
    key: str
    id: UUID
    kind: Literal["app", "form", "agent"]
    name: str
    description: str | None = None
    icon: str
    logo_url: str | None = None
    logo_version: str | None = None
    organization_id: UUID | None
    organization_name: str
    href: str
    pinned: bool = False
    last_opened_at: datetime | None = None


class HomeCollectionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    icon: str = Field(default="folder", max_length=50, pattern=r"^[a-z][a-z0-9-]*$")
    shared: bool = False
    organization_id: UUID | None = None
    resource_keys: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("resource_keys")
    @classmethod
    def unique_keys(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("A resource can only appear once in a collection")
        return value


class HomeCollectionPublic(HomeCollectionWrite):
    id: UUID
    can_edit: bool
    organization_name: str | None = None


class HomeResponse(BaseModel):
    resources: list[HomeResource]
    collections: list[HomeCollectionPublic]


class HomePreferenceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pinned: bool | None = None
    opened: bool = False
