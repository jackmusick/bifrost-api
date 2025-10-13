# Bifrost Type Stubs

Type definitions for Bifrost workflow development. These provide IDE autocomplete and type hints without requiring the engine source code.

## Usage

### For workflow developers:

1. **Copy the stub file to your workspace:**
   ```bash
   cp bifrost.pyi /path/to/your/workspace/
   ```

2. **Import using the bifrost module:**
   ```python
   from bifrost import workflow, param, OrganizationContext

   @workflow(name="my_workflow", description="...")
   async def my_workflow(context: OrganizationContext):
       context.log("Hello World")  # Simple form (info level)
       return {"success": True}
   ```

3. **Your IDE will provide:**
   - Autocomplete for context methods
   - Type hints for parameters and return values
   - Inline documentation

### For VS Code users:

Alternatively, configure your Python path in `.vscode/settings.json`:

```json
{
    "python.analysis.extraPaths": [
        "/path/to/bifrost-integrations/workflows"
    ]
}
```

This gives you full type hints without copying any files.

## Regenerating stubs

If the engine API changes, regenerate the stubs:

```bash
# From workflows directory
pip install mypy
stubgen -p engine.shared.context -p engine.shared.decorators -p engine.shared.models -o /tmp/stubs

# Then manually combine and clean up the relevant parts into bifrost.pyi
```

## What's included

- **OrganizationContext**: Context object passed to workflows
  - Configuration access (`get_config`)
  - OAuth connections (`get_oauth_connection`)
  - Logging (`log`)
  - State tracking (`save_checkpoint`, `set_variable`)

- **Decorators**:
  - `@workflow`: Register workflow functions
  - `@param`: Define workflow parameters
  - `@data_provider`: Create dynamic option providers

- **Models**:
  - `OAuthCredentials`: OAuth token handling
  - `ExecutionStatus`: Workflow execution states
  - `Organization`, `Caller`: Context data classes

## Runtime vs Development

- **Development time**: `bifrost.pyi` type stub provides IDE hints
- **Runtime**: `bifrost.py` shim re-exports from engine modules

Both files provide the same import pattern (`from bifrost import ...`), ensuring consistency between development and runtime.

The stubs and real implementation are kept in sync automatically.
