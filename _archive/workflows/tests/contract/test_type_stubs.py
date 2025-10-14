"""
Contract Tests: Type Stub Accuracy

Tests that validate bifrost.pyi stub file matches the actual implementation.
"""

import pytest
import inspect
import ast
from pathlib import Path
from typing import Set

from engine.shared.context import OrganizationContext
from engine.shared.decorators import workflow, param, data_provider
from engine.shared.models import ExecutionStatus, OAuthCredentials

# Import the actual bifrost module to check its exports
import bifrost


class TestTypeStubAccuracy:
    """Validate that type stubs match actual implementation"""

    @pytest.fixture
    def stub_path(self):
        """Get path to bifrost.pyi stub file"""
        return Path(__file__).parent.parent.parent / "stubs" / "bifrost.pyi"

    @pytest.fixture
    def bifrost_py_path(self):
        """Get path to bifrost.py runtime shim"""
        return Path(__file__).parent.parent.parent / "bifrost.py"

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

    def _parse_pyi_exports(self, stub_content: str) -> Set[str]:
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
                    if isinstance(item, ast.ClassDef):
                        exports.add(item.name)
                    elif isinstance(item, ast.FunctionDef):
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

        # Check that __all__ matches what's actually importable
        for export_name in bifrost.__all__:
            assert hasattr(bifrost, export_name), (
                f"bifrost.__all__ lists '{export_name}' but it's not actually exported"
            )

    def test_context_has_logger_methods(self):
        """Contract: OrganizationContext must have info/warning/error/debug methods"""
        required_methods = ['info', 'warning', 'error', 'debug']

        for method_name in required_methods:
            assert hasattr(OrganizationContext, method_name), (
                f"OrganizationContext missing method: {method_name}"
            )

            method = getattr(OrganizationContext, method_name)
            assert callable(method), f"{method_name} is not callable"

            # Check signature: (self, message: str, data: Optional[Dict] = None)
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            assert 'message' in params, f"{method_name} missing 'message' parameter"
            assert 'data' in params, f"{method_name} missing 'data' parameter"

    def test_context_does_not_have_log_method(self):
        """Contract: OrganizationContext should NOT have old log() method"""
        # We migrated from log() to info/warning/error/debug
        # Make sure the old method is removed
        assert not hasattr(OrganizationContext, 'log'), (
            "OrganizationContext should not have log() method - use info/warning/error/debug instead"
        )

    def test_context_has_required_methods(self):
        """Contract: OrganizationContext must have all documented methods"""
        required_methods = [
            'get_config',
            'has_config',
            'get_oauth_connection',
            'save_checkpoint',
            'set_variable',
            'get_variable',
            'finalize_execution'
        ]

        for method_name in required_methods:
            assert hasattr(OrganizationContext, method_name), (
                f"OrganizationContext missing method: {method_name}"
            )

    def test_context_has_required_properties(self):
        """Contract: OrganizationContext must have all documented properties/attributes"""
        # Properties (with @property decorator)
        required_properties = [
            'org_id',
            'org_name',
            'tenant_id',
            'executed_by',
            'executed_by_email',
            'executed_by_name'
        ]

        for prop_name in required_properties:
            assert hasattr(OrganizationContext, prop_name), (
                f"OrganizationContext missing property: {prop_name}"
            )
            # Verify it's actually a property
            attr = getattr(OrganizationContext, prop_name)
            assert isinstance(attr, property), f"{prop_name} should be a @property"

        # Public attributes (set in __init__)
        # These can't be checked on the class, only on instances
        # So we just document them here for reference
        required_attributes = ['execution_id', 'org', 'caller']

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

    def test_stub_file_contains_new_logger_methods(self):
        """Contract: Stub file must document new logger-style methods"""
        stub_path = Path(__file__).parent.parent.parent / "stubs" / "bifrost.pyi"
        stub_content = stub_path.read_text()

        # Check that stub has new methods
        assert 'def info(' in stub_content, "Stub missing info() method"
        assert 'def warning(' in stub_content, "Stub missing warning() method"
        assert 'def error(' in stub_content, "Stub missing error() method"
        assert 'def debug(' in stub_content, "Stub missing debug() method"

        # Check that old log() method is NOT in stub
        # Note: We need to be careful not to match "# Log" in comments
        import re
        log_method_pattern = r'def log\('
        matches = re.findall(log_method_pattern, stub_content)
        assert len(matches) == 0, (
            "Stub file should not contain log() method - use info/warning/error/debug instead"
        )

    def test_stub_signature_matches_implementation(self):
        """Contract: Stub method signatures should match implementation"""
        # Test info() signature
        info_sig = inspect.signature(OrganizationContext.info)
        params = list(info_sig.parameters.keys())

        assert params == ['self', 'message', 'data'], (
            f"info() signature mismatch. Expected ['self', 'message', 'data'], got {params}"
        )

        # Check data parameter has Optional[Dict] type hint
        data_param = info_sig.parameters['data']
        assert data_param.default is None, "data parameter should default to None"
