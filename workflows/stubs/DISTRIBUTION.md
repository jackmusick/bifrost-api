# Type Stubs Distribution

The `bifrost.pyi` type stub file is automatically published with each GitHub release for easy consumption by workflow developers.

## For Users

### Download from GitHub Release

The easiest way to get the type stubs:

```bash
# Download latest type stubs
curl -LO https://github.com/jackmusick/bifrost-integrations/releases/latest/download/bifrost.pyi

# Copy to your workspace
cp bifrost.pyi /workspace/bifrost.pyi
```

### Usage in Your Workflows

```python
from bifrost import workflow, param, OrganizationContext

@workflow(name="my_workflow", description="My workflow")
async def my_workflow(context: OrganizationContext):
    context.info("Hello World")  # IDE will autocomplete this!
    return {"success": True}
```

## For Maintainers

### How It Works

The `.github/workflows/build-release.yml` workflow automatically:

1. **Builds the workflows package** - Creates `workflows-latest.zip`
2. **Extracts type stubs** - Copies `workflows/stubs/bifrost.pyi` to root
3. **Uploads as artifact** - Saves `bifrost.pyi` as a build artifact
4. **Includes in release** - Attaches `bifrost.pyi` to the GitHub release

### Triggering a Release

Create a new release by pushing a version tag:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Or use the GitHub UI to create a release manually.

### Updating Type Stubs

When you update the API in `engine/shared/context.py` or other modules:

1. Update `workflows/stubs/bifrost.pyi` to match
2. Commit and push changes
3. Create a new release (see above)
4. Users can download the updated stubs from the new release

### Files Published

Each release includes:
- `api-latest.zip` - API function app package
- `workflows-latest.zip` - Workflows function app package
- `bifrost.pyi` - Type stubs for workflow development

## Benefits

- **Easy distribution** - Single file download from GitHub releases
- **Version tracking** - Each release has versioned type stubs
- **No repository access needed** - Users don't need to clone the repo
- **IDE support** - Full autocomplete without engine source code
- **Consistent DX** - Same import pattern in development and production
