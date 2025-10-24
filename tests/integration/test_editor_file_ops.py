"""
Integration tests for editor file operations.

Tests the file_operations.py module with actual file system operations.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from shared.editor.file_operations import (
    get_org_repo_path,
    validate_and_resolve_path,
    list_directory,
    read_file,
    write_file,
)
from shared.models import FileType


class TestFileOperations:
    """Integration tests for file operations module"""

    @pytest.fixture
    def temp_org_repo(self, monkeypatch):
        """Create a temporary organization repository for testing"""
        # Create temp directory
        temp_dir = tempfile.mkdtemp(prefix="test_editor_")

        # Create org directory structure
        org_id = "test-org"
        org_path = Path(temp_dir) / "orgs" / org_id / "repo"
        org_path.mkdir(parents=True, exist_ok=True)

        # Monkeypatch get_org_repo_path to use temp directory
        def mock_get_org_repo_path(org_id_param: str) -> Path:
            return (Path(temp_dir) / "orgs" / org_id_param / "repo").resolve()

        monkeypatch.setattr(
            "shared.editor.file_operations.get_org_repo_path",
            mock_get_org_repo_path,
        )

        # Create some test files and folders
        (org_path / "workflows").mkdir(exist_ok=True)
        (org_path / "data_providers").mkdir(exist_ok=True)
        (org_path / "workflows" / "sync_users.py").write_text(
            "import bifrost\n\ndef run(context):\n    pass"
        )
        (org_path / "workflows" / "sync_orders.py").write_text(
            "import bifrost\n\ndef run(context):\n    pass"
        )
        (org_path / "data_providers" / "get_users.py").write_text(
            "import bifrost\n\ndef run(context, parameters):\n    return []"
        )

        yield {
            "temp_dir": temp_dir,
            "org_id": org_id,
            "org_path": org_path,
        }

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_validate_and_resolve_path_valid(self, temp_org_repo):
        """Test path validation with valid paths"""
        org_id = temp_org_repo["org_id"]

        # Valid paths
        path = validate_and_resolve_path(org_id, "workflows/sync_users.py")
        assert path.exists()
        assert path.name == "sync_users.py"

        # Root directory
        path = validate_and_resolve_path(org_id, "")
        assert path.exists()
        assert path.is_dir()

    def test_validate_and_resolve_path_directory_traversal(self, temp_org_repo):
        """Test path validation rejects directory traversal attempts"""
        org_id = temp_org_repo["org_id"]

        # Attempt directory traversal
        with pytest.raises(ValueError, match="Path outside repository"):
            validate_and_resolve_path(org_id, "../../../etc/passwd")

        with pytest.raises(ValueError, match="Path outside repository"):
            validate_and_resolve_path(org_id, "workflows/../../etc/passwd")

    def test_list_directory_root(self, temp_org_repo):
        """Test listing root directory"""
        org_id = temp_org_repo["org_id"]

        files = list_directory(org_id, "")

        # Should have 2 folders
        assert len(files) == 2
        folder_names = {f.name for f in files if f.type == FileType.FOLDER}
        assert "workflows" in folder_names
        assert "data_providers" in folder_names

        # Check folder properties
        workflows = [f for f in files if f.name == "workflows"][0]
        assert workflows.type == FileType.FOLDER
        assert workflows.size is None
        assert workflows.extension is None

    def test_list_directory_workflows(self, temp_org_repo):
        """Test listing workflows directory"""
        org_id = temp_org_repo["org_id"]

        files = list_directory(org_id, "workflows")

        # Should have 2 Python files
        assert len(files) == 2
        file_names = {f.name for f in files}
        assert "sync_users.py" in file_names
        assert "sync_orders.py" in file_names

        # Check file properties
        sync_users = [f for f in files if f.name == "sync_users.py"][0]
        assert sync_users.type == FileType.FILE
        assert sync_users.extension == ".py"
        assert sync_users.size is not None
        assert sync_users.size > 0
        assert "workflows/sync_users.py" in sync_users.path

    def test_list_directory_not_found(self, temp_org_repo):
        """Test listing non-existent directory"""
        org_id = temp_org_repo["org_id"]

        with pytest.raises(FileNotFoundError):
            list_directory(org_id, "non_existent_folder")

    def test_list_directory_file_not_dir(self, temp_org_repo):
        """Test listing a file (not a directory) raises error"""
        org_id = temp_org_repo["org_id"]

        with pytest.raises(ValueError, match="Not a directory"):
            list_directory(org_id, "workflows/sync_users.py")

    def test_read_file_success(self, temp_org_repo):
        """Test reading file content"""
        org_id = temp_org_repo["org_id"]

        response = read_file(org_id, "workflows/sync_users.py")

        assert response.path == "workflows/sync_users.py"
        assert "import bifrost" in response.content
        assert response.encoding == "utf-8"
        assert response.size > 0
        assert response.etag is not None
        assert len(response.etag) > 0
        assert response.modified is not None

    def test_read_file_not_found(self, temp_org_repo):
        """Test reading non-existent file"""
        org_id = temp_org_repo["org_id"]

        with pytest.raises(FileNotFoundError):
            read_file(org_id, "workflows/non_existent.py")

    def test_read_file_directory(self, temp_org_repo):
        """Test reading a directory (not a file) raises error"""
        org_id = temp_org_repo["org_id"]

        with pytest.raises(ValueError, match="Not a file"):
            read_file(org_id, "workflows")

    def test_write_file_new(self, temp_org_repo):
        """Test writing a new file"""
        org_id = temp_org_repo["org_id"]
        org_path = temp_org_repo["org_path"]

        content = "import bifrost\n\ndef run(context):\n    context.info('New workflow')"
        response = write_file(org_id, "workflows/new_workflow.py", content)

        assert response.path == "workflows/new_workflow.py"
        assert response.content == content
        assert response.encoding == "utf-8"
        assert response.size == len(content.encode("utf-8"))
        assert response.etag is not None

        # Verify file actually exists
        file_path = org_path / "workflows" / "new_workflow.py"
        assert file_path.exists()
        assert file_path.read_text() == content

    def test_write_file_update_existing(self, temp_org_repo):
        """Test updating an existing file"""
        org_id = temp_org_repo["org_id"]
        org_path = temp_org_repo["org_path"]

        # Read original content
        original = read_file(org_id, "workflows/sync_users.py")
        original_etag = original.etag

        # Write new content
        new_content = "import bifrost\n\ndef run(context):\n    context.info('Updated')"
        response = write_file(org_id, "workflows/sync_users.py", new_content)

        assert response.content == new_content
        assert response.etag != original_etag  # ETag should change

        # Verify file content
        file_path = org_path / "workflows" / "sync_users.py"
        assert file_path.read_text() == new_content

    def test_write_file_creates_parent_directory(self, temp_org_repo):
        """Test writing file creates parent directories"""
        org_id = temp_org_repo["org_id"]
        org_path = temp_org_repo["org_path"]

        content = "test content"
        response = write_file(org_id, "new_folder/subfolder/test.py", content)

        assert response.path == "new_folder/subfolder/test.py"

        # Verify directories and file exist
        file_path = org_path / "new_folder" / "subfolder" / "test.py"
        assert file_path.exists()
        assert file_path.read_text() == content

    def test_write_file_atomic(self, temp_org_repo):
        """Test atomic write behavior"""
        org_id = temp_org_repo["org_id"]
        org_path = temp_org_repo["org_path"]

        # Write file
        content = "test content"
        write_file(org_id, "workflows/atomic_test.py", content)

        # Verify temp file doesn't exist after write
        file_path = org_path / "workflows" / "atomic_test.py"
        temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

        assert file_path.exists()
        assert not temp_path.exists()  # Temp file should be removed

    def test_write_file_rejects_non_utf8_encoding(self, temp_org_repo):
        """Test write_file rejects non-UTF-8 encoding"""
        org_id = temp_org_repo["org_id"]

        with pytest.raises(ValueError, match="Only UTF-8 encoding is supported"):
            write_file(
                org_id, "workflows/test.py", "content", encoding="latin-1"
            )
