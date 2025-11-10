"""
Editor File Operations API
Handles file browsing, reading, and writing for browser-based code editor
Thin wrapper - business logic is in shared.editor.file_operations
"""

import asyncio
import json
import logging

import azure.functions as func

from shared.editor.file_operations import (
    list_directory,
    read_file,
    write_file,
)
from shared.editor.search import search_files
from shared.models import (
    FileMetadata,
    FileContentRequest,
    FileContentResponse,
    SearchRequest,
    SearchResponse,
)
from shared.openapi_decorators import openapi_endpoint

logger = logging.getLogger(__name__)

# Create blueprint for editor file endpoints
bp = func.Blueprint()


@bp.route(route="editor/files", methods=["GET"])
@bp.function_name("editor_list_files")
@openapi_endpoint(
    path="/editor/files",
    method="GET",
    summary="List files in directory",
    description="List files and folders in /home directory (platform admin resource)",
    tags=["Editor"],
    response_model=list[FileMetadata],
    query_params={
        "path": {
            "description": "Relative path to directory (empty = root)",
            "schema": {"type": "string"},
            "required": False,
        }
    },
)
async def editor_list_files(req: func.HttpRequest) -> func.HttpResponse:
    """
    List files and folders in a directory.

    Returns FileMetadata array with file/folder information.
    """
    try:
        path = req.params.get("path", "")

        logger.info(f"Listing files, path: {path}")

        # list_directory is synchronous (stat operations are fast for local disk)
        # Only file read/write operations are async
        files = list_directory(path)

        # Convert to JSON
        files_json = [f.model_dump() for f in files]

        return func.HttpResponse(
            body=json.dumps(files_json),
            status_code=200,
            mimetype="application/json",
        )

    except FileNotFoundError as e:
        logger.warning(f"Directory not found: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "NotFound", "message": str(e)}),
            status_code=404,
            mimetype="application/json",
        )
    except ValueError as e:
        logger.warning(f"Invalid path: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error listing files: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to list files: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="editor/files/content", methods=["GET"])
@bp.function_name("editor_read_file")
@openapi_endpoint(
    path="/editor/files/content",
    method="GET",
    summary="Read file content",
    description="Read content of a file in /home directory (platform admin resource)",
    tags=["Editor"],
    response_model=FileContentResponse,
    query_params={
        "path": {
            "description": "Relative path to file",
            "schema": {"type": "string"},
            "required": True,
        }
    },
)
async def editor_read_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Read file content.

    Returns FileContentResponse with content and metadata.
    """
    try:
        path = req.params.get("path")

        if not path:
            return func.HttpResponse(
                body=json.dumps({"error": "BadRequest", "message": "Missing 'path' parameter"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Reading file, path: {path}")

        # read_file is now async
        response = await read_file(path)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except FileNotFoundError as e:
        logger.warning(f"File not found: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "NotFound", "message": str(e)}),
            status_code=404,
            mimetype="application/json",
        )
    except ValueError as e:
        logger.warning(f"Invalid file operation: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except PermissionError as e:
        logger.warning(f"Permission denied: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Forbidden", "message": str(e)}),
            status_code=403,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to read file: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="editor/files/content", methods=["PUT"])
@bp.function_name("editor_write_file")
@openapi_endpoint(
    path="/editor/files/content",
    method="PUT",
    summary="Write file content",
    description="Write or update file content in /home directory (platform admin resource)",
    tags=["Editor"],
    request_model=FileContentRequest,
    response_model=FileContentResponse,
)
async def editor_write_file(req: func.HttpRequest) -> func.HttpResponse:
    """
    Write file content.

    Creates new file or updates existing file. Parent directories are created automatically.
    Returns FileContentResponse with updated metadata.
    """
    try:
        # Parse request body
        body = json.loads(req.get_body().decode("utf-8"))
        write_request = FileContentRequest(**body)

        logger.info(
            f"Writing file, path: {write_request.path}, "
            f"size: {len(write_request.content)} bytes"
        )

        # Check for conflicts if client provided expected_etag
        if write_request.expected_etag:
            from shared.editor.file_operations import validate_and_resolve_path

            file_path = validate_and_resolve_path(write_request.path)

            # Check if file exists
            if not file_path.exists():
                # File was deleted on server
                from shared.models import FileConflictResponse
                conflict = FileConflictResponse(
                    reason="path_not_found",
                    message="File path no longer exists"
                )
                return func.HttpResponse(
                    body=conflict.model_dump_json(),
                    status_code=409,
                    mimetype="application/json",
                )

            # File exists - check if etag matches
            try:
                current_file = await read_file(write_request.path)
                if current_file.etag != write_request.expected_etag:
                    # Content changed on server
                    from shared.models import FileConflictResponse
                    conflict = FileConflictResponse(
                        reason="content_changed",
                        message="File content has changed on the server"
                    )
                    return func.HttpResponse(
                        body=conflict.model_dump_json(),
                        status_code=409,
                        mimetype="application/json",
                    )
            except Exception as e:
                # If we can't read the file for comparison, log and proceed with write
                logger.warning(f"Could not read file for etag comparison: {e}")

        # No conflict detected - proceed with write
        response = await write_file(
            write_request.path,
            write_request.content,
            write_request.encoding,
        )

        # Trigger immediate module reload for Python files (eliminates watcher lag)
        if write_request.path.endswith('.py'):
            try:
                from pathlib import Path
                from function_app import reload_single_module
                from shared.editor.file_operations import validate_and_resolve_path

                # Get absolute path to the file
                file_path = validate_and_resolve_path(write_request.path)

                # Trigger reload (don't wait for filesystem watcher)
                reload_single_module(Path(file_path))
                logger.info(f"Triggered immediate module reload for {write_request.path}")
            except Exception as e:
                # Log warning but don't fail the save
                logger.warning(f"Failed to trigger reload after save: {e}", exc_info=True)

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except json.JSONDecodeError:
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json",
        )
    except ValueError as e:
        logger.warning(f"Invalid write operation: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except PermissionError as e:
        logger.warning(f"Permission denied: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Forbidden", "message": str(e)}),
            status_code=403,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error writing file: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to write file: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="editor/folder", methods=["POST"])
@bp.function_name("editor_create_folder")
@openapi_endpoint(
    path="/editor/folder",
    method="POST",
    summary="Create folder",
    description="Create a new folder in /home directory (platform admin resource)",
    tags=["Editor"],
    query_params={
        "path": {
            "description": "Relative path to folder to create",
            "schema": {"type": "string"},
            "required": True,
        }
    },
    response_model=FileMetadata,
)
async def editor_create_folder(req: func.HttpRequest) -> func.HttpResponse:
    """
    Create a new folder.

    Returns FileMetadata for the created folder.
    """
    try:
        path = req.params.get("path")

        if not path:
            return func.HttpResponse(
                body=json.dumps({"error": "BadRequest", "message": "Missing 'path' parameter"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Creating folder, path: {path}")

        from shared.editor.file_operations import create_folder

        # Run blocking I/O in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        folder = await loop.run_in_executor(None, create_folder, path)

        return func.HttpResponse(
            body=folder.model_dump_json(),
            status_code=201,
            mimetype="application/json",
        )

    except ValueError as e:
        logger.warning(f"Invalid folder creation: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except PermissionError as e:
        logger.warning(f"Permission denied: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Forbidden", "message": str(e)}),
            status_code=403,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error creating folder: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to create folder: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="editor/path", methods=["DELETE"])
@bp.function_name("editor_delete_path")
@openapi_endpoint(
    path="/editor/path",
    method="DELETE",
    summary="Delete file or folder",
    description="Delete a file or folder in /home directory (platform admin resource)",
    tags=["Editor"],
    query_params={
        "path": {
            "description": "Relative path to file or folder to delete",
            "schema": {"type": "string"},
            "required": True,
        }
    },
)
async def editor_delete_path(req: func.HttpRequest) -> func.HttpResponse:
    """
    Delete a file or folder.

    Returns 204 No Content on success.
    """
    try:
        path = req.params.get("path")

        if not path:
            return func.HttpResponse(
                body=json.dumps({"error": "BadRequest", "message": "Missing 'path' parameter"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Deleting path, path: {path}")

        from shared.editor.file_operations import delete_path

        # Run blocking I/O in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, delete_path, path)

        return func.HttpResponse(
            status_code=204,
        )

    except FileNotFoundError as e:
        logger.warning(f"Path not found: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "NotFound", "message": str(e)}),
            status_code=404,
            mimetype="application/json",
        )
    except ValueError as e:
        logger.warning(f"Invalid delete operation: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except PermissionError as e:
        logger.warning(f"Permission denied: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Forbidden", "message": str(e)}),
            status_code=403,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error deleting path: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to delete path: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="editor/path/rename", methods=["PUT"])
@bp.function_name("editor_rename_path")
@openapi_endpoint(
    path="/editor/path/rename",
    method="PUT",
    summary="Rename or move file/folder",
    description="Rename or move a file or folder in /home directory (platform admin resource)",
    tags=["Editor"],
    query_params={
        "oldPath": {
            "description": "Current relative path",
            "schema": {"type": "string"},
            "required": True,
        },
        "newPath": {
            "description": "New relative path",
            "schema": {"type": "string"},
            "required": True,
        }
    },
    response_model=FileMetadata,
)
async def editor_rename_path(req: func.HttpRequest) -> func.HttpResponse:
    """
    Rename or move a file or folder.

    Returns FileMetadata for the renamed/moved item.
    """
    try:
        old_path = req.params.get("oldPath")
        new_path = req.params.get("newPath")

        if not old_path or not new_path:
            return func.HttpResponse(
                body=json.dumps({"error": "BadRequest", "message": "Missing 'oldPath' or 'newPath' parameter"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Renaming path, from: {old_path}, to: {new_path}")

        from shared.editor.file_operations import rename_path

        # rename_path is async, call it directly
        result = await rename_path(old_path, new_path)

        return func.HttpResponse(
            body=result.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except FileNotFoundError as e:
        logger.warning(f"Path not found: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "NotFound", "message": str(e)}),
            status_code=404,
            mimetype="application/json",
        )
    except ValueError as e:
        logger.warning(f"Invalid rename operation: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except PermissionError as e:
        logger.warning(f"Permission denied: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "Forbidden", "message": str(e)}),
            status_code=403,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error renaming path: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to rename path: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )


@bp.route(route="editor/search", methods=["POST"])
@bp.function_name("editor_search_files")
@openapi_endpoint(
    path="/editor/search",
    method="POST",
    summary="Search file contents",
    description="Search for text or regex patterns across files in /home directory (platform admin resource)",
    tags=["Editor"],
    request_model=SearchRequest,
    response_model=SearchResponse,
)
async def editor_search_files(req: func.HttpRequest) -> func.HttpResponse:
    """
    Search file contents for matching text or regex patterns.

    Supports:
    - Text search with optional case sensitivity
    - Regex pattern matching
    - File pattern filtering (glob)
    - Context lines before/after matches
    - Parallel processing for fast results

    Returns SearchResponse with matches and metadata.
    """
    try:
        # Parse request body
        body = json.loads(req.get_body().decode("utf-8"))
        search_request = SearchRequest(**body)

        logger.info(
            f"Searching files, query: '{search_request.query}', "
            f"case sensitive: {search_request.caseSensitive}, "
            f"regex: {search_request.regex}, "
            f"file pattern: {search_request.filePattern}"
        )

        # Run blocking I/O in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, search_files, search_request)

        logger.info(
            f"Search complete, matches: {response.totalMatches}, "
            f"files searched: {response.filesSearched}, "
            f"time: {response.searchTimeMs}ms"
        )

        return func.HttpResponse(
            body=response.model_dump_json(),
            status_code=200,
            mimetype="application/json",
        )

    except json.JSONDecodeError:
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": "Invalid JSON in request body"}),
            status_code=400,
            mimetype="application/json",
        )
    except ValueError as e:
        logger.warning(f"Invalid search request: {str(e)}")
        return func.HttpResponse(
            body=json.dumps({"error": "BadRequest", "message": str(e)}),
            status_code=400,
            mimetype="application/json",
        )
    except Exception as e:
        logger.error(f"Error searching files: {str(e)}", exc_info=True)
        return func.HttpResponse(
            body=json.dumps({
                "error": "InternalServerError",
                "message": f"Failed to search files: {str(e)}",
            }),
            status_code=500,
            mimetype="application/json",
        )
