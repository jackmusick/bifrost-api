# Custom Packages: Install & Import Testing

## Overview

The Bifrost platform supports installing custom Python packages at runtime. Packages are installed to `/home/.packages` and shared across all workflows.

## How It Works

1. **Startup**: `function_app.py` creates `/home/.packages` directory and adds it to `sys.path`
2. **Installation**: Workflows can use `subprocess` to run `pip install --target=/home/.packages <package>`
3. **Import**: After installation, workflows can import packages normally
4. **Sharing**: All workflows in all orgs share the same packages (workspace-level, not org-level)

## Testing

### Automated Test Workflow

**File:** `/home/repo/test_custom_packages_runtime.py`

**Usage:**
```bash
POST /api/workflows/test_custom_packages_runtime/execute
{
    "inputData": {
        "package": "colorama",
        "test_import": true,
        "test_usage": true
    }
}
```

**What It Tests:**
1. ✓ `.packages` directory exists
2. ✓ Package can be installed via `pip install --target`
3. ✓ Package can be imported after installation
4. ✓ **Package is imported from `.packages`** (verifies `__file__` path)
5. ✓ Package functions work correctly
6. ✓ `.packages` is in `sys.path` (at runtime)

**Recommended Test Packages (NOT in requirements.txt):**
- `colorama` - Terminal color formatting (DEFAULT - best test)
- `tabulate` - Table formatting
- `python-dateutil` - Date parsing
- `pyyaml` - YAML parsing

**Packages to AVOID for Testing:**
- ❌ `requests` - Already in requirements.txt (can't verify .packages import)
- ❌ `pydantic` - Already in requirements.txt
- ❌ `azure-*` - Already in requirements.txt

### Manual Testing Steps

#### 1. Install a Package

```python
# In a workflow
import subprocess
import sys
from pathlib import Path

packages_dir = Path("/home/.packages")  # Adjust path for your environment

result = subprocess.run(
    [sys.executable, "-m", "pip", "install", "--target", str(packages_dir), "requests"],
    capture_output=True,
    text=True
)

print(result.stdout)
```

#### 2. Import and Use the Package

```python
# In the same workflow or a different one
import requests

response = requests.get("https://api.github.com")
print(f"Status: {response.status_code}")
```

#### 3. Verify Installation Persists

```python
# In another workflow execution (even different org)
import requests  # Should work without reinstalling

print(requests.__version__)
```

## Expected Results

### First Execution (Package Not Installed)
```json
{
    "success": true,
    "package": "colorama",
    "steps": [
        {
            "step": "verify_packages_dir",
            "status": "success",
            "path": "/home/.packages"
        },
        {
            "step": "check_existing",
            "status": "not_installed",
            "message": "colorama is not installed"
        },
        {
            "step": "install",
            "status": "success",
            "message": "Successfully installed colorama"
        },
        {
            "step": "test_import",
            "status": "success",
            "message": "Successfully imported colorama",
            "module_file": "/home/.packages/colorama/__init__.py",
            "from_packages": true
        },
        {
            "step": "test_usage",
            "status": "success",
            "test": "Terminal color formatting",
            "has_fore": true,
            "has_back": true,
            "has_style": true
        }
    ],
    "summary": {
        "already_installed": false,
        "import_successful": true,
        "usage_successful": true,
        "all_successful": true
    }
}
```

### Subsequent Executions (Package Already Installed)
```json
{
    "success": true,
    "package": "colorama",
    "steps": [
        {
            "step": "verify_packages_dir",
            "status": "success"
        },
        {
            "step": "check_existing",
            "status": "already_installed",
            "message": "colorama is already installed"
        },
        {
            "step": "test_import",
            "status": "success",
            "module_file": "/home/.packages/colorama/__init__.py",
            "from_packages": true
        },
        {
            "step": "test_usage",
            "status": "success",
            "test": "Terminal color formatting"
        }
    ],
    "summary": {
        "already_installed": true,
        "all_successful": true
    }
}
```

## Package Isolation

### Current Design: Workspace-Level (Shared)

**All workflows share the same packages:**
- Org A installs `requests` → Org B can also use `requests`
- Simplifies package management
- Reduces disk usage
- Faster subsequent imports (already in memory)

**Implications:**
- Package versions are shared (cannot have org-A use requests==2.28 and org-B use requests==2.31)
- Package installation is first-come-first-served
- Workflows should handle missing packages gracefully

### Future: Org-Level Isolation (If Needed)

If org-level isolation becomes necessary:

1. **Directory Structure:**
   ```
   /home/.packages/
       org-123/
           requests/
           pyyaml/
       org-456/
           requests/
           python-dateutil/
   ```

2. **sys.path Modification:**
   ```python
   # In workflow execution, dynamically add org-specific path
   org_packages = f"/home/.packages/{context.org_id}"
   sys.path.insert(0, org_packages)
   ```

3. **Installation:**
   ```python
   pip install --target=/home/.packages/{org_id} <package>
   ```

**Not currently implemented** - workspace-level sharing is simpler and sufficient for most use cases.

## Security Considerations

### ✓ Safe
- Packages installed to `/home/.packages` (not system-wide)
- Import restrictions still enforced (can only import from bifrost.*, not shared.*)
- Path sandboxing still enforced (file operations restricted to /home/files and /home/tmp)

### ⚠️ Risks
- Malicious packages could be installed (trusted developer responsibility)
- Version conflicts between orgs (mitigated by shared environment)
- Disk space usage (all packages accumulate in .packages)

### 🔒 Recommendations
1. **Trust**: Only trusted developers should write workflows
2. **Review**: Code review workflow changes before deployment
3. **Monitoring**: Monitor .packages disk usage
4. **Cleanup**: Periodically clean unused packages
5. **Pinning**: Use `requirements.txt` with pinned versions for reproducibility

## Troubleshooting

### Import Error After Installation

**Problem:** Package installs successfully but import fails

**Solution:**
```python
# Ensure .packages is in sys.path
import sys
from pathlib import Path

packages_dir = Path("/home/.packages")
if str(packages_dir) not in sys.path:
    sys.path.insert(0, str(packages_dir))

# Then import
import your_package
```

### Version Conflicts

**Problem:** Org A needs requests==2.28, Org B needs requests==2.31

**Current Solution:** Not supported - use workspace-level version
**Future Solution:** Implement org-level isolation (see above)

### Package Not Found After Restart

**Problem:** Package was installed but disappeared after function app restart

**Cause:** .packages directory is ephemeral in some deployment environments
**Solution:** Use `requirements.txt` in `/home/repo/` and install on startup

## Requirements.txt Support (Future)

Planned feature:

1. **Create requirements.txt:**
   ```
   # /home/repo/requirements.txt
   requests==2.31.0
   python-dateutil==2.8.2
   pyyaml==6.0.1
   ```

2. **Auto-install on startup:**
   ```python
   # In function_app.py
   requirements_file = Path("/home/repo/requirements.txt")
   if requirements_file.exists():
       subprocess.run([
           sys.executable, "-m", "pip", "install",
           "--target", str(packages_dir),
           "-r", str(requirements_file)
       ])
   ```

3. **Benefits:**
   - Reproducible package versions
   - Easy onboarding (just sync repo)
   - No manual installation needed

**Not currently implemented** - can be added if needed.

## Summary

✅ **What Works:**
- Install packages at runtime via `pip install --target`
- Import packages in workflows
- Packages shared across all workflows/orgs
- Tested with workflow: `test_custom_packages_runtime`

⚠️ **Limitations:**
- Workspace-level sharing (not org-isolated)
- Version conflicts not handled
- Manual installation required (no auto-install from requirements.txt yet)

🔒 **Security:**
- Trusted developer model
- Import restrictions still enforced
- Path sandboxing still enforced
