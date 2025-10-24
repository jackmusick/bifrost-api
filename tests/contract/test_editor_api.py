"""
Contract tests for editor API endpoints

Tests file operations, search, and editor-related models.
"""

import pytest
from pydantic import ValidationError
from shared.models import (
    FileMetadata,
    FileType,
    FileContentRequest,
    FileContentResponse,
    SearchRequest,
    SearchResult,
    SearchResponse,
)


class TestEditorModelContracts:
    """Contract tests for editor API models"""

    def test_file_metadata_model_structure(self):
        """Test that FileMetadata model has required fields"""
        file = FileMetadata(
            path="workflows/test.py",
            name="test.py",
            type=FileType.FILE,
            size=1024,
            extension=".py",
            modified="2025-10-23T14:30:00Z",
            isReadOnly=False,
        )

        assert file.path == "workflows/test.py"
        assert file.name == "test.py"
        assert file.type == FileType.FILE
        assert file.size == 1024
        assert file.extension == ".py"
        assert file.modified == "2025-10-23T14:30:00Z"
        assert file.isReadOnly is False

    def test_file_metadata_folder_type(self):
        """Test FileMetadata for folder type"""
        folder = FileMetadata(
            path="workflows",
            name="workflows",
            type=FileType.FOLDER,
            size=None,
            extension=None,
            modified="2025-10-23T14:30:00Z",
            isReadOnly=False,
        )

        assert folder.type == FileType.FOLDER
        assert folder.size is None
        assert folder.extension is None

    def test_file_content_request_model(self):
        """Test FileContentRequest model structure"""
        request = FileContentRequest(
            path="workflows/test.py",
            content="import bifrost\n\ndef run(context):\n    pass",
            encoding="utf-8",
        )

        assert request.path == "workflows/test.py"
        assert "import bifrost" in request.content
        assert request.encoding == "utf-8"

    def test_file_content_request_default_encoding(self):
        """Test FileContentRequest uses utf-8 by default"""
        request = FileContentRequest(
            path="workflows/test.py", content="test content"
        )

        assert request.encoding == "utf-8"

    def test_file_content_response_model(self):
        """Test FileContentResponse model structure"""
        response = FileContentResponse(
            path="workflows/test.py",
            content="import bifrost",
            encoding="utf-8",
            size=14,
            etag="abc123",
            modified="2025-10-23T14:30:00Z",
        )

        assert response.path == "workflows/test.py"
        assert response.content == "import bifrost"
        assert response.encoding == "utf-8"
        assert response.size == 14
        assert response.etag == "abc123"
        assert response.modified == "2025-10-23T14:30:00Z"

    def test_search_request_model(self):
        """Test SearchRequest model structure"""
        request = SearchRequest(
            query="def run",
            caseSensitive=False,
            regex=False,
            filePattern="**/*.py",
            maxResults=100,
        )

        assert request.query == "def run"
        assert request.caseSensitive is False
        assert request.regex is False
        assert request.filePattern == "**/*.py"
        assert request.maxResults == 100

    def test_search_request_defaults(self):
        """Test SearchRequest default values"""
        request = SearchRequest(query="test")

        assert request.caseSensitive is False
        assert request.regex is False
        assert request.filePattern == "**/*"
        assert request.maxResults == 1000

    def test_search_request_validates_query_not_empty(self):
        """Test SearchRequest rejects empty query"""
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_search_request_validates_max_results_range(self):
        """Test SearchRequest validates maxResults is within range"""
        # Valid range
        SearchRequest(query="test", maxResults=1)
        SearchRequest(query="test", maxResults=10000)

        # Too low
        with pytest.raises(ValidationError):
            SearchRequest(query="test", maxResults=0)

        # Too high
        with pytest.raises(ValidationError):
            SearchRequest(query="test", maxResults=10001)

    def test_search_result_model(self):
        """Test SearchResult model structure"""
        result = SearchResult(
            filePath="workflows/sync.py",
            line=42,
            column=15,
            matchText="def run",
            contextBefore="# Sync workflow",
            contextAfter="    context.info('Starting')",
        )

        assert result.filePath == "workflows/sync.py"
        assert result.line == 42
        assert result.column == 15
        assert result.matchText == "def run"
        assert result.contextBefore == "# Sync workflow"
        assert result.contextAfter == "    context.info('Starting')"

    def test_search_result_optional_context(self):
        """Test SearchResult with optional context fields"""
        result = SearchResult(
            filePath="workflows/sync.py",
            line=1,
            column=0,
            matchText="import",
            contextBefore=None,
            contextAfter=None,
        )

        assert result.contextBefore is None
        assert result.contextAfter is None

    def test_search_result_validates_line_number(self):
        """Test SearchResult validates line >= 1"""
        # Valid line numbers
        SearchResult(
            filePath="test.py",
            line=1,
            column=0,
            matchText="test",
        )

        # Invalid line number (must be >= 1)
        with pytest.raises(ValidationError):
            SearchResult(
                filePath="test.py",
                line=0,
                column=0,
                matchText="test",
            )

    def test_search_result_validates_column_number(self):
        """Test SearchResult validates column >= 0"""
        # Valid column numbers
        SearchResult(
            filePath="test.py",
            line=1,
            column=0,
            matchText="test",
        )

        # Invalid column number (must be >= 0)
        with pytest.raises(ValidationError):
            SearchResult(
                filePath="test.py",
                line=1,
                column=-1,
                matchText="test",
            )

    def test_search_response_model(self):
        """Test SearchResponse model structure"""
        results = [
            SearchResult(
                filePath="test1.py",
                line=10,
                column=5,
                matchText="test",
            ),
            SearchResult(
                filePath="test2.py",
                line=20,
                column=8,
                matchText="test",
            ),
        ]

        response = SearchResponse(
            query="test",
            totalMatches=2,
            filesSearched=50,
            results=results,
            truncated=False,
            searchTimeMs=123,
        )

        assert response.query == "test"
        assert response.totalMatches == 2
        assert response.filesSearched == 50
        assert len(response.results) == 2
        assert response.truncated is False
        assert response.searchTimeMs == 123

    def test_search_response_truncated_results(self):
        """Test SearchResponse with truncated results"""
        response = SearchResponse(
            query="test",
            totalMatches=5000,
            filesSearched=1000,
            results=[],  # Truncated
            truncated=True,
            searchTimeMs=456,
        )

        assert response.totalMatches == 5000
        assert len(response.results) == 0
        assert response.truncated is True

    def test_file_type_enum_values(self):
        """Test FileType enum has correct values"""
        assert FileType.FILE == "file"
        assert FileType.FOLDER == "folder"

        # Enum should only have these two values
        assert len(list(FileType)) == 2
