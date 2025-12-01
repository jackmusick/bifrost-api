"""Tests for Code Editor file filtering logic."""

import pytest
from pathlib import Path

from shared.editor.file_operations import (
    _is_real_file,
    HIDDEN_DIRECTORIES,
    HIDDEN_FILES,
    HIDDEN_EXTENSIONS,
    HIDDEN_PREFIXES,
)


class TestIsRealFile:
    """Tests for _is_real_file function."""

    def test_regular_file_returns_true(self, tmp_path: Path):
        """Regular files should be shown."""
        test_file = tmp_path / "test.py"
        test_file.touch()
        assert _is_real_file(test_file) is True

    def test_regular_directory_returns_true(self, tmp_path: Path):
        """Regular directories should be shown."""
        test_dir = tmp_path / "src"
        test_dir.mkdir()
        assert _is_real_file(test_dir) is True

    # Hidden directories
    @pytest.mark.parametrize("dirname", list(HIDDEN_DIRECTORIES))
    def test_hidden_directories_filtered(self, tmp_path: Path, dirname: str):
        """Hidden directories should be filtered out."""
        hidden_dir = tmp_path / dirname
        hidden_dir.mkdir()
        assert _is_real_file(hidden_dir) is False

    # Hidden files
    @pytest.mark.parametrize("filename", list(HIDDEN_FILES))
    def test_hidden_files_filtered(self, tmp_path: Path, filename: str):
        """Hidden files should be filtered out."""
        hidden_file = tmp_path / filename
        hidden_file.touch()
        assert _is_real_file(hidden_file) is False

    # Hidden extensions
    @pytest.mark.parametrize("extension", list(HIDDEN_EXTENSIONS))
    def test_hidden_extensions_filtered(self, tmp_path: Path, extension: str):
        """Files with hidden extensions should be filtered out."""
        hidden_file = tmp_path / f"module{extension}"
        hidden_file.touch()
        assert _is_real_file(hidden_file) is False

    # Hidden prefixes (AppleDouble files)
    def test_appledouble_files_filtered(self, tmp_path: Path):
        """AppleDouble metadata files (._*) should be filtered out."""
        appledouble = tmp_path / "._test.py"
        appledouble.touch()
        assert _is_real_file(appledouble) is False

    def test_appledouble_directory_filtered(self, tmp_path: Path):
        """AppleDouble metadata directories should be filtered out."""
        appledouble = tmp_path / "._cache"
        appledouble.mkdir()
        assert _is_real_file(appledouble) is False

    # Edge cases
    def test_env_file_not_filtered(self, tmp_path: Path):
        """.env files should NOT be filtered (developers need them)."""
        env_file = tmp_path / ".env"
        env_file.touch()
        assert _is_real_file(env_file) is True

    def test_env_local_file_not_filtered(self, tmp_path: Path):
        """.env.local files should NOT be filtered."""
        env_file = tmp_path / ".env.local"
        env_file.touch()
        assert _is_real_file(env_file) is True

    def test_gitignore_file_not_filtered(self, tmp_path: Path):
        """.gitignore files should NOT be filtered."""
        gitignore = tmp_path / ".gitignore"
        gitignore.touch()
        assert _is_real_file(gitignore) is True

    def test_hidden_extension_case_insensitive(self, tmp_path: Path):
        """Hidden extensions should be case insensitive."""
        pyc_upper = tmp_path / "module.PYC"
        pyc_upper.touch()
        assert _is_real_file(pyc_upper) is False

    def test_directory_named_like_hidden_file_is_filtered(self, tmp_path: Path):
        """Directory with same name as hidden file is also filtered.

        HIDDEN_FILES filter matches by name regardless of type,
        so a directory named 'bifrost.pyi' would also be filtered.
        """
        weird_dir = tmp_path / "bifrost.pyi"
        weird_dir.mkdir()
        # Name match happens before type-specific checks
        assert _is_real_file(weird_dir) is False

    def test_file_named_like_hidden_directory_not_filtered(self, tmp_path: Path):
        """File with same name as hidden directory should not be filtered.

        For example, a file called 'node_modules' should not be filtered
        since HIDDEN_DIRECTORIES only applies to directories.
        """
        weird_file = tmp_path / "node_modules"
        weird_file.touch()
        # File check only applies to directories, so this file should pass
        assert _is_real_file(weird_file) is True


class TestHiddenPatternConstants:
    """Tests for the hidden pattern constants."""

    def test_hidden_directories_not_empty(self):
        """HIDDEN_DIRECTORIES should contain expected values."""
        assert '.git' in HIDDEN_DIRECTORIES
        assert '__pycache__' in HIDDEN_DIRECTORIES
        assert 'node_modules' in HIDDEN_DIRECTORIES
        assert '.vscode' in HIDDEN_DIRECTORIES

    def test_hidden_files_not_empty(self):
        """HIDDEN_FILES should contain expected values."""
        assert '.DS_Store' in HIDDEN_FILES
        assert 'Thumbs.db' in HIDDEN_FILES
        assert 'bifrost.pyi' in HIDDEN_FILES

    def test_hidden_extensions_not_empty(self):
        """HIDDEN_EXTENSIONS should contain expected values."""
        assert '.pyc' in HIDDEN_EXTENSIONS
        assert '.pyo' in HIDDEN_EXTENSIONS

    def test_hidden_prefixes_contains_appledouble(self):
        """HIDDEN_PREFIXES should contain AppleDouble prefix."""
        assert '._' in HIDDEN_PREFIXES
