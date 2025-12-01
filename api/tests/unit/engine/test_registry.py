"""
Unit tests for shared/discovery module.
Tests workflow and data provider discovery from workspace files.
"""


from shared.discovery import (
    WorkflowMetadata,
    DataProviderMetadata,
    WorkflowParameter,
    scan_all_workflows,
    scan_all_data_providers,
    scan_all_forms,
    load_workflow,
    load_data_provider,
    load_form,
    get_form_metadata,
    get_forms_by_workflow,
    get_workspace_paths,
)


class TestWorkflowMetadata:
    """Test WorkflowMetadata dataclass"""

    def test_create_metadata_minimal(self):
        """Test creating metadata with minimal fields"""
        metadata = WorkflowMetadata(
            name="test_workflow",
            description="Test workflow"
        )

        assert metadata.name == "test_workflow"
        assert metadata.description == "Test workflow"
        assert metadata.category == "General"
        assert metadata.tags == []
        assert metadata.execution_mode == "sync"
        assert metadata.parameters == []
        assert metadata.function is None

    def test_create_metadata_full(self):
        """Test creating metadata with all fields"""
        def test_func():
            pass

        param = WorkflowParameter(name="test", type="string")

        metadata = WorkflowMetadata(
            name="user_onboarding",
            description="Onboard users",
            category="user_management",
            tags=["m365", "user"],
            execution_mode="async",
            parameters=[param],
            function=test_func
        )

        assert metadata.name == "user_onboarding"
        assert metadata.category == "user_management"
        assert metadata.tags == ["m365", "user"]
        assert metadata.execution_mode == "async"
        assert len(metadata.parameters) == 1
        assert metadata.function is test_func


class TestWorkflowParameter:
    """Test WorkflowParameter dataclass"""

    def test_create_parameter_minimal(self):
        """Test creating parameter with minimal fields"""
        param = WorkflowParameter(
            name="test_param",
            type="string"
        )

        assert param.name == "test_param"
        assert param.type == "string"
        assert param.label is None
        assert param.required is False
        assert param.validation is None
        assert param.data_provider is None
        assert param.default_value is None
        assert param.help_text is None

    def test_create_parameter_full(self):
        """Test creating parameter with all fields"""
        param = WorkflowParameter(
            name="email",
            type="email",
            label="Email Address",
            required=True,
            validation={"pattern": r"^[a-zA-Z0-9._%+-]+@"},
            data_provider=None,
            default_value="test@example.com",
            help_text="Enter your email address"
        )

        assert param.name == "email"
        assert param.type == "email"
        assert param.label == "Email Address"
        assert param.required is True
        assert "pattern" in param.validation
        assert param.default_value == "test@example.com"
        assert param.help_text == "Enter your email address"


class TestDataProviderMetadata:
    """Test DataProviderMetadata dataclass"""

    def test_create_provider_metadata_minimal(self):
        """Test creating provider metadata with minimal fields"""
        metadata = DataProviderMetadata(
            name="test_provider",
            description="Test provider"
        )

        assert metadata.name == "test_provider"
        assert metadata.description == "Test provider"
        assert metadata.category == "General"
        assert metadata.cache_ttl_seconds == 300
        assert metadata.function is None

    def test_create_provider_metadata_full(self):
        """Test creating provider metadata with all fields"""
        def test_func():
            pass

        metadata = DataProviderMetadata(
            name="get_available_licenses",
            description="Returns available licenses",
            category="m365",
            cache_ttl_seconds=600,
            function=test_func
        )

        assert metadata.name == "get_available_licenses"
        assert metadata.category == "m365"
        assert metadata.cache_ttl_seconds == 600
        assert metadata.function is test_func


class TestDiscoveryFunctions:
    """Test discovery functions"""

    def test_get_workspace_paths_no_env(self, monkeypatch):
        """Test workspace paths when no env var is set"""
        monkeypatch.delenv("BIFROST_WORKSPACE_LOCATION", raising=False)
        paths = get_workspace_paths()
        # Should still return platform path
        assert any("platform" in str(p) for p in paths)

    def test_scan_all_workflows_empty_workspace(self, monkeypatch, tmp_path):
        """Test scanning empty workspace"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        workflows = scan_all_workflows()
        # Platform workflows will still be found
        assert isinstance(workflows, list)

    def test_scan_all_data_providers_empty_workspace(self, monkeypatch, tmp_path):
        """Test scanning empty workspace for data providers"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        providers = scan_all_data_providers()
        # Platform providers will still be found
        assert isinstance(providers, list)

    def test_load_workflow_not_found(self, monkeypatch, tmp_path):
        """Test loading non-existent workflow"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        result = load_workflow("nonexistent_workflow")
        assert result is None

    def test_load_data_provider_not_found(self, monkeypatch, tmp_path):
        """Test loading non-existent data provider"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        result = load_data_provider("nonexistent_provider")
        assert result is None


class TestFormDiscovery:
    """Test form discovery functions"""

    def test_scan_all_forms_empty_workspace(self, monkeypatch, tmp_path):
        """Test scanning empty workspace for forms"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        forms = scan_all_forms()
        assert isinstance(forms, list)

    def test_load_form_not_found(self, monkeypatch, tmp_path):
        """Test loading non-existent form"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        result = load_form("nonexistent_form_id")
        assert result is None

    def test_get_form_metadata_not_found(self, monkeypatch, tmp_path):
        """Test getting metadata for non-existent form"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        result = get_form_metadata("nonexistent_form_id")
        assert result is None

    def test_get_forms_by_workflow_empty(self, monkeypatch, tmp_path):
        """Test getting forms by workflow when none exist"""
        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        forms = get_forms_by_workflow("some_workflow")
        assert forms == []

    def test_scan_forms_from_file(self, monkeypatch, tmp_path):
        """Test scanning forms from actual file"""
        import json

        # Create a test form file
        form_data = {
            "id": "test-form-123",
            "name": "Test Form",
            "linkedWorkflow": "test_workflow",
            "orgId": "GLOBAL",
            "isActive": True,
            "isGlobal": True,
            "accessLevel": "public",
            "formSchema": {"title": "Test"},
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z"
        }

        form_file = tmp_path / "test.form.json"
        with open(form_file, 'w') as f:
            json.dump(form_data, f)

        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        forms = scan_all_forms()

        # Find our test form
        test_form = next((f for f in forms if f.id == "test-form-123"), None)
        assert test_form is not None
        assert test_form.name == "Test Form"
        assert test_form.linked_workflow == "test_workflow"
        assert test_form.is_global is True

    def test_load_form_from_file(self, monkeypatch, tmp_path):
        """Test loading form from file"""
        import json

        form_data = {
            "id": "load-test-form",
            "name": "Load Test Form",
            "linkedWorkflow": "test_workflow",
            "formSchema": {"title": "Test"}
        }

        form_file = tmp_path / "load-test.form.json"
        with open(form_file, 'w') as f:
            json.dump(form_data, f)

        monkeypatch.setenv("BIFROST_WORKSPACE_LOCATION", str(tmp_path))
        result = load_form("load-test-form")

        assert result is not None
        assert result["id"] == "load-test-form"
        assert result["name"] == "Load Test Form"
