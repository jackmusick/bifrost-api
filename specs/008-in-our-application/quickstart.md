# Quick Start: Browser-Based Code Editor

**Feature**: Browser-Based Code Editor
**Date**: 2025-10-23

This guide helps developers set up and test the browser-based code editor locally.

## Prerequisites

- Docker (for Azurite)
- Node.js 18+ and npm
- Python 3.11+
- Azure Functions Core Tools v4

## Local Development Setup

### 1. Start Azure Storage Emulator

```bash
# Start Azurite (Azure Storage Emulator)
docker compose up azurite
```

This provides local emulation of:
- Azure Table Storage (for workspace session locks)
- Azure Blob Storage (for large execution logs)

### 2. Set Up Backend (Python Azure Functions)

```bash
cd api

# Install Python dependencies
pip install -r requirements.txt

# Create local settings for Functions
cat > local.settings.json <<EOF
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_STORAGE_CONNECTION_STRING": "UseDevelopmentStorage=true"
  }
}
EOF

# Start Azure Functions locally
func start
```

The Functions app will start on `http://localhost:7071`.

### 3. Set Up Frontend (React + TypeScript)

```bash
cd client

# Install dependencies
npm install

# Install new editor dependencies
npm install @monaco-editor/react @atlaskit/pragmatic-drag-and-drop zustand

# Generate TypeScript types from API (ensure func is running)
npm run generate:types

# Start development server
npm run dev
```

The frontend will start on `http://localhost:5173`.

### 4. Create Test Files

```bash
# Create test workspace
mkdir -p /home/repo/workflows
mkdir -p /home/repo/data_providers

# Create a sample workflow
cat > /home/repo/workflows/test_workflow.py <<EOF
import bifrost

def run(context):
    context.info("Test workflow starting")
    context.info(f"Organization: {context.org_id}")
    context.info("Test workflow complete")
    return {"status": "success"}
EOF

# Create a sample data provider
cat > /home/repo/data_providers/test_provider.py <<EOF
import bifrost

def run(context, parameters):
    context.info("Test data provider starting")
    return [
        {"id": 1, "name": "Item 1"},
        {"id": 2, "name": "Item 2"}
    ]
EOF
```

## Using the Editor

### 1. Open the Editor

Navigate to `http://localhost:5173/editor` in your browser.

The editor will:
1. Automatically attempt to acquire a workspace lock
2. Create `/home/repo` if it doesn't exist
3. Load the file tree

### 2. Browse Files

- Click on folders to expand/collapse
- Click on files to open in the Monaco editor
- Use the file tree to navigate your workspace

### 3. Edit Files

- Open any `.py` file
- Make changes in the Monaco editor
- File auto-saves after 5 seconds of inactivity
- Or press `Ctrl+S` (Windows/Linux) or `Cmd+S` (Mac) to save manually
- Watch for the unsaved indicator to clear after save

### 4. File Operations

**Create new file**:
1. Right-click on a folder
2. Select "New File"
3. Enter filename
4. File opens in editor

**Create new folder**:
1. Right-click on a folder
2. Select "New Folder"
3. Enter folder name

**Rename**:
1. Right-click on file/folder
2. Select "Rename"
3. Enter new name

**Delete**:
1. Right-click on file/folder
2. Select "Delete"
3. Confirm deletion

**Move (drag-and-drop)**:
1. Click and hold on file/folder
2. Drag to target folder
3. Release to move

### 5. Search Files

1. Click the Search icon in the left sidebar
2. Enter search term
3. Click "Search" or press Enter
4. Click on results to jump to that location in the file

**Search options**:
- Case sensitive toggle
- Regex toggle (for advanced patterns)
- File pattern filter (e.g., `**/*.py` for Python files only)

### 6. Execute Workflows

1. Click the Run icon in the left sidebar
2. Select a workflow file from the dropdown
3. Fill in required parameters (uses existing "Run Workflow" form)
4. Click "Execute"
5. Terminal panel opens automatically showing real-time logs

**Terminal features**:
- Resize by dragging the top border
- Scroll through output
- Search within terminal (`Ctrl+F`)
- Auto-scrolls to show latest logs

### 7. Monitor Execution

Watch the terminal for:
- Log levels (INFO, WARNING, ERROR colored differently)
- Timestamps on each log line
- Execution completion status

### 8. Minimize Editor

- Click the minimize button (bottom-right of editor)
- Editor collapses to a corner widget
- Click widget to restore full editor

## Testing the Feature

### Manual Testing Checklist

**File Operations**:
- [ ] Open editor, verify `/home/repo` is created
- [ ] Create a new file, verify it appears in tree
- [ ] Edit file, wait 5s, verify auto-save indicator
- [ ] Manually save with Ctrl+S, verify save
- [ ] Rename a file, verify tree updates
- [ ] Delete a file, verify it's removed
- [ ] Drag file to different folder, verify move

**Search**:
- [ ] Search for text across files
- [ ] Verify results show file path, line number, context
- [ ] Click result, verify file opens at correct line
- [ ] Try case-sensitive search
- [ ] Try regex search pattern

**Execution**:
- [ ] Execute test workflow
- [ ] Verify logs appear in terminal in real-time
- [ ] Verify timestamps on logs
- [ ] Try terminal search (Ctrl+F)
- [ ] Resize terminal panel

**Session Locking**:
- [ ] Open editor in one browser
- [ ] Try to open in another browser/tab
- [ ] Verify "workspace locked" error with user info
- [ ] Close first browser
- [ ] Verify second browser can now acquire lock (after timeout)

### Running Automated Tests

```bash
# Backend contract tests
cd api
./test.sh tests/contract/test_editor_api.py

# Backend integration tests
./test.sh tests/integration/test_editor_file_ops.py
./test.sh tests/integration/test_editor_execution.py

# Frontend E2E tests
cd client
npm run test:e2e
```

## Common Issues

### Editor doesn't load

**Problem**: Blank screen or endless loading
**Solution**:
1. Check browser console for errors
2. Verify Functions app is running (`http://localhost:7071`)
3. Check network tab for failed API calls
4. Verify CORS is configured in Functions

### Cannot acquire workspace lock

**Problem**: "Workspace is locked" error
**Solution**:
1. Check Azure Table Storage (Azurite) is running
2. Check for stale locks in `WorkspaceSessions` table
3. Wait 5 minutes for lock to expire
4. Or manually delete lock from Table Storage

### File operations fail

**Problem**: 403 or 500 errors on file operations
**Solution**:
1. Verify `/home` directory exists and is writable
2. Check file permissions
3. Verify `X-Organization-Id` header is being sent
4. Check user has `editor:access` permission for org

### Execution logs don't stream

**Problem**: No logs appear in terminal
**Solution**:
1. Check browser supports SSE (all modern browsers do)
2. Verify SSE endpoint returns `text/event-stream` content type
3. Check browser console for connection errors
4. Verify workflow is actually running (check backend logs)

### Monaco editor performance issues

**Problem**: Editor is slow with large files
**Solution**:
1. Check file size (>5MB triggers warnings)
2. Minimap is disabled for files >5MB automatically
3. Consider breaking large files into smaller modules

## API Endpoints Reference

All endpoints require `X-Organization-Id` header.

### File Operations (`/api/editor/files`)

- `GET /api/editor/files?path={path}` - List directory contents
- `GET /api/editor/files/content?path={path}` - Read file
- `PUT /api/editor/files/content` - Write file
- `POST /api/editor/files` - Create file/folder
- `POST /api/editor/files/delete` - Delete file/folder
- `POST /api/editor/files/rename` - Rename file/folder
- `POST /api/editor/files/move` - Move file/folder

### Workspace Sessions (`/api/editor/sessions`)

- `POST /api/editor/sessions` - Acquire lock
- `DELETE /api/editor/sessions/{sessionId}` - Release lock
- `PUT /api/editor/sessions/{sessionId}/heartbeat` - Renew lock
- `GET /api/editor/sessions` - List active sessions

### Search (`/api/editor/search`)

- `POST /api/editor/search` - Search file contents

### Execution (`/api/editor/execute`)

- `POST /api/editor/execute` - Execute file
- `GET /api/editor/execute/{executionId}/logs` - Stream logs (SSE)
- `GET /api/editor/execute/{executionId}/status` - Get status

## Next Steps

1. Run automated tests to verify all functionality
2. Test with real workflows and data providers
3. Test concurrent access (multiple users/browsers)
4. Load test with large file trees (500+ files)
5. Test search with large codebases (10,000+ lines)

## Development Tips

### Hot Reload

- Frontend: Changes auto-reload via Vite HMR
- Backend: Functions app auto-reloads on Python file changes
- Types: Re-run `npm run generate:types` after API changes

### Debugging

**Frontend**:
- Use React DevTools browser extension
- Check browser console for errors
- Use Network tab to inspect API calls

**Backend**:
- Add `import pdb; pdb.set_trace()` for breakpoints
- Check Functions app console for Python errors
- Use `context.info()` for debug logging

### Component Development

The editor is composed of these main React components:
- `EditorLayout.tsx` - Main container with sidebar + editor + terminal
- `FileTree.tsx` - File browser with drag-and-drop
- `CodeEditor.tsx` - Monaco editor wrapper
- `SearchPanel.tsx` - File search UI
- `RunPanel.tsx` - Execution panel with forms
- `Terminal.tsx` - Read-only terminal with log display
- `StatusBar.tsx` - Bottom status bar

Each component can be developed/tested independently.

---

**Ready to start building!** Follow the setup steps, create test files, and start exploring the editor.
