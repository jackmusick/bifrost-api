"""
Editor Files Router

File operations for browser-based code editor.
Provides safe file I/O with path validation.
Platform admin resource - no org scoping.
"""

import logging

from fastapi import APIRouter, Query, HTTPException, status

from src.models.schemas import FileContentRequest, FileContentResponse, FileMetadata
from shared.editor.file_operations import (
    list_directory,
    read_file,
    write_file,
    delete_path,
    create_folder,
    rename_path,
)
from src.core.auth import Context, CurrentSuperuser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/editor", tags=["Editor"])


# =============================================================================
# HTTP Endpoints
# =============================================================================


@router.get(
    "/files",
    response_model=list[FileMetadata],
    summary="List directory contents",
    description="List files and folders in a directory (Platform admin only)",
)
async def list_files(
    path: str = Query(..., description="Directory path relative to workspace root"),
    ctx: Context = None,
    user: CurrentSuperuser = None,
) -> list[FileMetadata]:
    """
    List files and folders in a directory.

    Args:
        path: Directory path relative to workspace root

    Returns:
        List of file and folder metadata
    """
    try:
        files = list_directory(path)
        logger.info(f"Listed directory: {path} ({len(files)} items)")
        return files
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Directory not found: {path}",
        )
    except Exception as e:
        logger.error(f"Error listing directory {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list directory",
        )


@router.get(
    "/files/content",
    response_model=FileContentResponse,
    summary="Read file content",
    description="Read the content of a file (Platform admin only)",
)
async def get_file_content(
    path: str = Query(..., description="File path relative to workspace root"),
    ctx: Context = None,
    user: CurrentSuperuser = None,
) -> FileContentResponse:
    """
    Read file content.

    Args:
        path: File path relative to workspace root

    Returns:
        File content and metadata
    """
    try:
        result = await read_file(path)
        logger.info(f"Read file: {path} ({result.size} bytes)")
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {path}",
        )
    except Exception as e:
        logger.error(f"Error reading file {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read file",
        )


@router.put(
    "/files/content",
    response_model=FileContentResponse,
    summary="Write file content",
    description="Write content to a file (Platform admin only)",
)
async def put_file_content(
    request: FileContentRequest,
    ctx: Context = None,
    user: CurrentSuperuser = None,
) -> FileContentResponse:
    """
    Write content to a file.

    Args:
        request: File content request with path and content

    Returns:
        Updated file metadata
    """
    try:
        await write_file(request.path, request.content, request.encoding)
        logger.info(f"Wrote file: {request.path} ({len(request.content)} bytes)")

        return FileContentResponse(
            path=request.path,
            content=request.content,
            encoding=request.encoding,
            size=len(request.content),
            etag="",
            modified="",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error writing file {request.path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to write file",
        )


@router.post(
    "/files/folder",
    response_model=FileMetadata,
    status_code=status.HTTP_201_CREATED,
    summary="Create folder",
    description="Create a new folder (Platform admin only)",
)
async def create_new_folder(
    path: str = Query(..., description="Folder path relative to workspace root"),
    ctx: Context = None,
    user: CurrentSuperuser = None,
) -> FileMetadata:
    """
    Create a new folder.

    Args:
        path: Folder path relative to workspace root

    Returns:
        Folder metadata
    """
    try:
        folder_meta = create_folder(path)
        logger.info(f"Created folder: {path}")
        return folder_meta
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Folder already exists: {path}",
        )
    except Exception as e:
        logger.error(f"Error creating folder {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create folder",
        )


@router.delete(
    "/files",
    summary="Delete file or folder",
    description="Delete a file or folder recursively (Platform admin only)",
)
async def delete_file_or_directory(
    path: str = Query(..., description="File or folder path relative to workspace root"),
    ctx: Context = None,
    user: CurrentSuperuser = None,
) -> dict:
    """
    Delete a file or folder.

    Args:
        path: File or folder path relative to workspace root

    Returns:
        Confirmation message
    """
    try:
        delete_path(path)
        logger.info(f"Deleted: {path}")
        return {"message": f"Successfully deleted: {path}"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File or folder not found: {path}",
        )
    except Exception as e:
        logger.error(f"Error deleting {path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file or folder",
        )


@router.post(
    "/files/rename",
    response_model=FileMetadata,
    summary="Rename or move file/folder",
    description="Rename or move a file or folder (Platform admin only)",
)
async def rename_or_move(
    old_path: str = Query(..., description="Current path relative to workspace root"),
    new_path: str = Query(..., description="New path relative to workspace root"),
    ctx: Context = None,
    user: CurrentSuperuser = None,
) -> FileMetadata:
    """
    Rename or move a file or folder.

    Args:
        old_path: Current path relative to workspace root
        new_path: New path relative to workspace root

    Returns:
        Updated file metadata
    """
    try:
        file_meta = await rename_path(old_path, new_path)
        logger.info(f"Renamed: {old_path} -> {new_path}")
        return file_meta
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File or folder not found: {old_path}",
        )
    except FileExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Destination already exists: {new_path}",
        )
    except Exception as e:
        logger.error(f"Error renaming {old_path}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to rename file or folder",
        )
