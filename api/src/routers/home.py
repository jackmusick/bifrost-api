"""Authenticated launcher and collection endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Response

from shared import home
from src.core.auth import CurrentActiveUser
from src.core.db_deps import DbSession
from src.models.contracts.home import HomeCollectionPublic, HomeCollectionWrite, HomePreferenceWrite, HomeResponse

router = APIRouter(prefix="/api/home", tags=["Home"])


def require_workspace_user(user: CurrentActiveUser) -> None:
    if user.embed:
        raise HTTPException(403, "Embedded sessions cannot access Home")


@router.get("", response_model=HomeResponse)
async def get_home(user: CurrentActiveUser, db: DbSession) -> HomeResponse:
    require_workspace_user(user)
    return await home.get_home(db, user)


@router.post("/collections", response_model=HomeCollectionPublic, status_code=201)
async def create_collection(data: HomeCollectionWrite, user: CurrentActiveUser, db: DbSession) -> HomeCollectionPublic:
    require_workspace_user(user)
    return await home.save_collection(db, user, data)


@router.put("/collections/{collection_id}", response_model=HomeCollectionPublic)
async def update_collection(collection_id: UUID, data: HomeCollectionWrite, user: CurrentActiveUser, db: DbSession) -> HomeCollectionPublic:
    require_workspace_user(user)
    return await home.save_collection(db, user, data, collection_id)


@router.delete("/collections/{collection_id}", status_code=204)
async def delete_collection(collection_id: UUID, user: CurrentActiveUser, db: DbSession) -> Response:
    require_workspace_user(user)
    row = await home.get_collection(db, user, collection_id, require_edit=True)
    await db.delete(row)
    return Response(status_code=204)


@router.put("/preferences/{resource_key}", status_code=204)
async def update_preference(resource_key: str, data: HomePreferenceWrite, user: CurrentActiveUser, db: DbSession) -> Response:
    require_workspace_user(user)
    await home.save_preference(db, user, resource_key, data)
    return Response(status_code=204)
