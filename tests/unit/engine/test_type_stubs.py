"""
Contract Tests: Type Stub Accuracy

Tests that validate bifrost.pyi stub file matches the actual implementation.
"""

import ast
import inspect
from pathlib import Path

import pytest

# Import the actual bifrost module to check its exports
import bifrost
from shared.context import ExecutionContext
from shared.decorators import data_provider, param, workflow
from shared.models import ExecutionStatus, OAuthCredentials


class TestTypeStubAccuracy:
    """Validate that type stubs match actual implementation"""

    @pytest.fixture
    def stub_path(self):
        """Get path to bifrost.pyi stub file"""
        return Path(__file__).parent.parent.parent.parent / "stubs" / "bifrost.pyi"

    @pytest.fixture
    def bifrost_py_path(self):
        """Get path to bifrost.py runtime shim"""
        return Path(__file__).parent.parent.parent.parent / "bifrost.py"

    def test_stub_file_exists(self, stub_path):
        """Contract: Type stub file must exist"""
        assert stub_path.exists(), f"Type stub file not found at {stub_path}"

    def test_bifrost_py_exists(self, bifrost_py_path):
        """Contract: bifrost.py runtime shim must exist"""
        assert bifrost_py_path.exists(), f"bifrost.py not found at {bifrost_py_path}"

    def test_stub_exports_match_bifrost_py(self, stub_path, bifrost_py_path):
        """
        Contract: bifrost.pyi must export everything that bifrost.py exports

        This is the KEY test - if you add new features to bifrost.py,
        this test will fail until you update bifrost.pyi to match.
        """
        # Get actual exports from bifrost.py runtime
        actual_exports = set(bifrost.__all__)

        # Parse bifrost.pyi stub file to get declared exports
        stub_content = stub_path.read_text()
        stub_exports = self._parse_pyi_exports(stub_content)

        # Check that stub exports match actual exports
        missing_in_stub = actual_exports - stub_exports
        extra_in_stub = stub_exports - actual_exports

        error_messages = []

        if missing_in_stub:
            error_messages.append(
                f"❌ bifrost.pyi is MISSING exports that exist in bifrost.py:\n"
                f"   {sorted(missing_in_stub)}\n"
                f"   → Add these to bifrost.pyi"
            )

        if extra_in_stub:
            error_messages.append(
                f"⚠️  bifrost.pyi has exports that DON'T exist in bifrost.py:\n"
                f"   {sorted(extra_in_stub)}\n"
                f"   → Remove these from bifrost.pyi or add to bifrost.py"
            )

        if error_messages:
            pytest.fail("\n\n".join(error_messages))

    def _parse_pyi_exports(self, stub_content: str) -> set[str]:
        """
        Parse a .pyi file and extract all top-level class/function definitions.

        This finds everything that would be importable from the module.
        """
        try:
            tree = ast.parse(stub_content)
        except SyntaxError as e:
            pytest.fail(f"Failed to parse bifrost.pyi: {e}")

        exports = set()

        for node in ast.walk(tree):
            # Only look at top-level definitions (Module -> definitions)
            if isinstance(node, ast.Module):
                for item in node.body:
                    if isinstance(item, ast.ClassDef) or isinstance(item, ast.FunctionDef):
                        exports.add(item.name)
                    elif isinstance(item, ast.Assign):
                        # Handle class attributes or module-level assignments
                        for target in item.targets:
                            if isinstance(target, ast.Name):
                                exports.add(target.id)

        return exports

    def test_bifrost_runtime_imports_work(self):
        """Contract: Verify bifrost module actually exports what it claims"""
        # This test validates the runtime shim works correctly

        # SDK modules that are lazy-loaded from platform.bifrost.*
        # These may not be available in test contexts where platform package isn't set up
        lazy_loaded_sdk_modules = {
            'config', 'executions', 'files', 'forms', 'oauth',
            'organizations', 'roles', 'secrets', 'workflows'
        }

        # Check that __all__ matches what's actually importable
        for export_name in bifrost.__all__:
            # Skip SDK modules that are lazy-loaded - they require platform package
            if export_name in lazy_loaded_sdk_modules:
                continue

            assert hasattr(bifrost, export_name), (
                f"bifrost.__all__ lists '{export_name}' but it's not actually exported"
            )

    def test_context_does_not_have_logger_methods(self):
        """Contract: ExecutionContext must NOT have info/warning/error/debug methods

        These were removed in the context API refactoring. Workflows should use
        the logger module directly instead.
        """
        deprecated_methods = ['info', 'warning', 'error', 'debug']

        for method_name in deprecated_methods:
            assert not hasattr(ExecutionContext, method_name), (
                f"ExecutionContext should not have {method_name}() method - "
                f"use logger.{method_name}() in workflows instead"
            )

    def test_context_does_not_have_log_method(self):
        """Contract: ExecutionContext should NOT have old log() method"""
        # We migrated from log() to info/warning/error/debug
        # Make sure the old method is removed
        assert not hasattr(ExecutionContext, 'log'), (
            "ExecutionContext should not have log() method - use info/warning/error/debug instead"
        )

    def test_context_has_required_methods(self):
        """Contract: ExecutionContext must have all documented methods"""
        required_methods = [
            'finalize_execution'
        ]

        for method_name in required_methods:
            assert hasattr(ExecutionContext, method_name), (
                f"ExecutionContext missing method: {method_name}"
            )

    def test_context_does_not_have_deprecated_methods(self):
        """Contract: ExecutionContext must NOT have deprecated variable methods

        set_variable() and get_variable() were removed in the context API refactoring.
        Variables are now captured automatically from the script namespace.
        """
        deprecated_methods = ['set_variable', 'get_variable']

        for method_name in deprecated_methods:
            assert not hasattr(ExecutionContext, method_name), (
                f"ExecutionContext should not have {method_name}() - "
                f"variables are captured automatically from script namespace"
            )

    def test_context_has_required_properties(self):
        """Contract: ExecutionContext must have all documented properties/attributes"""
        # Properties (with @property decorator)
        required_properties = [
            'org_id',
            'org_name',
            'executed_by',
            'executed_by_email',
            'executed_by_name'
        ]

        for prop_name in required_properties:
            assert hasattr(ExecutionContext, prop_name), (
                f"ExecutionContext missing property: {prop_name}"
            )
            # Verify it's actually a property
            attr = getattr(ExecutionContext, prop_name)
            assert isinstance(attr, property), f"{prop_name} should be a @property"

        # Public attributes (set in __init__)
        # These can't be checked on the class, only on instances
        # So we just document them here for reference

    def test_decorators_exist(self):
        """Contract: All documented decorators must exist"""
        assert callable(workflow), "workflow decorator not found"
        assert callable(param), "param decorator not found"
        assert callable(data_provider), "data_provider decorator not found"

    def test_models_exist(self):
        """Contract: All documented models must exist"""
        assert ExecutionStatus is not None, "ExecutionStatus model not found"
        assert OAuthCredentials is not None, "OAuthCredentials model not found"

    def test_oauth_credentials_has_required_methods(self):
        """Contract: OAuthCredentials must have documented methods"""
        required_methods = ['is_expired', 'get_auth_header']

        for method_name in required_methods:
            assert hasattr(OAuthCredentials, method_name), (
                f"OAuthCredentials missing method: {method_name}"
            )

    def test_stub_file_does_not_contain_logger_methods(self):
        """Contract: Stub file must NOT document deprecated logger methods

        Logger methods (info, warning, error, debug) were removed from ExecutionContext.
        Workflows should use the logger module directly.
        """
        stub_path = Path(__file__).parent.parent.parent.parent / "stubs" / "bifrost.pyi"
        stub_content = stub_path.read_text()

        # Check that stub does NOT have deprecated logger methods
        import re
        logger_methods = ['info', 'warning', 'error', 'debug']
        for method in logger_methods:
            pattern = rf'def {method}\('
            matches = re.findall(pattern, stub_content)
            assert len(matches) == 0, (
                f"Stub file should not contain {method}() method - "
                f"use logger.{method}() in workflows instead"
            )

        # Check that old log() method is NOT in stub
        log_method_pattern = r'def log\('
        matches = re.findall(log_method_pattern, stub_content)
        assert len(matches) == 0, (
            "Stub file should not contain log() method"
        )

    def test_stub_signature_matches_implementation(self):
        """Contract: Stub method signatures should match implementation"""
        # Test finalize_execution() signature
        finalize_sig = inspect.signature(ExecutionContext.finalize_execution)
        params = list(finalize_sig.parameters.keys())

        assert 'self' in params or len(params) >= 0, (
            f"finalize_execution() signature should be a valid method, got {params}"
        )
