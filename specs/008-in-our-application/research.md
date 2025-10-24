# Technical Research: Browser-Based Code Editor

**Feature**: Browser-Based Code Editor
**Date**: 2025-10-23
**Status**: Completed (Revised - Simplified)

This document captures technical decisions for implementing a VS Code-like browser-based code editor.

## 1. Monaco Editor Integration

### Decision

Use `@monaco-editor/react` v4.6+ with the following configuration:
- **Package**: `@monaco-editor/react` (official React wrapper)
- **Monaco Version**: Use CDN-hosted Monaco (via package default) for smaller bundle
- **Languages**: Configure 15+ languages via Monaco's built-in language support
- **Auto-save**: Debounced save with 5-second delay using `lodash.debounce` or custom hook
- **Performance**: Lazy-load editor, use `onChange` debouncing, disable minimap for files >5MB

### Rationale

- **Official wrapper**: `@monaco-editor/react` is the official Microsoft package with excellent TypeScript support
- **CDN approach**: Reduces bundle size by ~3MB since Monaco is large; acceptable latency trade-off
- **Built-in languages**: Monaco includes syntax highlighting for all required languages out-of-box
- **Debounced save**: Prevents excessive API calls while ensuring changes aren't lost
- **Performance tuning**: Monaco handles large files well with proper configuration (disable expensive features)

### Configuration Example

```typescript
import Editor from '@monaco-editor/react';

<Editor
  height="100%"
  language={detectedLanguage}
  value={fileContent}
  onChange={debouncedSave}
  theme="vs-dark"
  options={{
    minimap: { enabled: fileSize < 5_000_000 }, // Disable for large files
    scrollBeyondLastLine: false,
    fontSize: 14,
    wordWrap: 'on',
    automaticLayout: true,
  }}
/>
```

### Alternatives Considered

- **CodeMirror 6**: More lightweight but less VS Code-like, missing some language features
- **Ace Editor**: Older, less maintained, inferior TypeScript support
- **Custom textarea**: Would require building all features from scratch, not viable

## 2. File Tree UI with Drag-and-Drop

### Decision

Use **Pragmatic drag and drop** (`@atlaskit/pragmatic-drag-and-drop`) for drag-and-drop functionality with a custom tree component or `react-complex-tree`.

- **Drag-and-drop**: `@atlaskit/pragmatic-drag-and-drop` (per user requirement)
- **Tree component**: `react-complex-tree` or custom recursive component
- **Virtual scrolling**: `react-window` if tree exceeds 1000+ items
- **Context menu**: Custom implementation using `onContextMenu` event + positioned div

### Rationale

- **Pragmatic DnD**: User-specified requirement; modern, performant, framework-agnostic approach from Atlassian
- **react-complex-tree**: Provides tree state management, keyboard navigation, excellent accessibility
- **Virtual scrolling**: Only needed for very large trees (500 items renders fine without virtualization)
- **Custom context menu**: Lightweight, full control over styling and behavior vs heavy library

### Integration Pattern

```typescript
import { draggable, dropTargetForElements } from '@atlaskit/pragmatic-drag-and-drop/element/adapter';

// In FileTreeItem component
useEffect(() => {
  const cleanup = combine(
    draggable({
      element: ref.current,
      getInitialData: () => ({ type: 'file', path: filePath }),
    }),
    dropTargetForElements({
      element: ref.current,
      onDrop: ({ source }) => handleMove(source.data.path, filePath),
    })
  );
  return cleanup;
}, [filePath]);
```

### Alternatives Considered

- **react-dnd**: More complex API, heavier bundle, less modern than Pragmatic DnD
- **dnd-kit**: Excellent library but user specified Pragmatic drag and drop
- **Native HTML5 DnD**: Browser inconsistencies, poor mobile support, limited customization

## 3. Workflow Execution Integration

### Decision

**Use existing workflow execution infrastructure** with synchronous REST responses:
- **Endpoint**: Use existing `/api/workflows/execute` (or similar existing endpoint)
- **Sync workflows**: Return results directly in HTTP response, display in terminal
- **Async workflows**: Return completion message with link to results page
- **No polling**: Sync workflows block until complete, async shows message immediately
- **Terminal display**: Rich formatting for sync results, simple message + link for async

### Rationale

- **Leverage existing code**: No need to duplicate execution logic, context loading, or logging
- **Consistent behavior**: Workflows behave the same whether run from editor or elsewhere
- **Simpler architecture**: No SSE, WebSockets, or polling complexity
- **Async handling**: Message with link is acceptable since editor can be minimized
- **Maintainability**: Single execution path means easier updates and bug fixes

### Implementation Pattern

**Sync Workflow Response**:
```json
{
  "executionId": "550e8400-...",
  "status": "completed",
  "logs": [
    {"timestamp": "2025-10-23T14:30:01Z", "level": "INFO", "message": "Starting sync"},
    {"timestamp": "2025-10-23T14:30:02Z", "level": "INFO", "message": "Sync complete"}
  ],
  "result": {"status": "success", "usersUpdated": 42}
}
```

**Async Workflow Response**:
```json
{
  "executionId": "550e8400-...",
  "status": "queued",
  "message": "Executed async workflow. Review results at /executions/550e8400-...",
  "resultsUrl": "/executions/550e8400-..."
}
```

**Terminal Display**:
```typescript
// Sync: Display all logs
logs.forEach(log => terminal.appendLine(`[${log.level}] ${log.message}`));

// Async: Display message with clickable link/button
terminal.appendLine(
  `✓ Workflow queued. ` +
  `<a href="${resultsUrl}">View results</a> | ` +
  `<button onclick="refreshResults('${executionId}')">Refresh</button>`
);
```

### Alternatives Considered

- **SSE streaming**: Azure Functions timeout limitations (230s on Consumption), adds complexity
- **Polling**: Unnecessary for sync workflows, added latency and server load
- **WebSockets**: Requires SignalR service, overkill for this use case
- **New execution path**: Would diverge from existing infrastructure, maintenance burden

### Integration Requirements

Need to identify in existing codebase:
1. Workflow execution endpoint path (e.g., `/api/workflows/execute`)
2. Request format (filePath, parameters, orgId)
3. Response format for sync vs async workflows
4. How to fetch execution results later (for async refresh button)

## 4. File System Operations

### Decision

Use **standard Python file I/O** for Azure File Share operations:
- **Library**: Built-in Python `open()`, `os`, `pathlib` - no aiofiles needed
- **File operations**: Standard synchronous I/O is fast enough for code files
- **Atomic writes**: Write to temp file → rename pattern
- **Path validation**: Use `Path.resolve()` and `is_relative_to()` to prevent traversal
- **Error handling**: Try/except with specific error messages for permission, disk full

### Rationale

- **Simple and reliable**: Standard library is battle-tested, no external dependencies
- **Fast enough**: Azure File Share latency is acceptable for code files (<10MB)
- **Synchronous is fine**: Azure Functions can handle blocking I/O for quick operations
- **Path safety**: `pathlib` provides secure path manipulation
- **Clear errors**: Specific exception handling provides better UX than generic errors

### Implementation Pattern

```python
from pathlib import Path

def read_file_safe(org_id: str, file_path: str) -> str:
    """Read file with path validation"""
    base_path = Path(f"/home/orgs/{org_id}/repo").resolve()
    full_path = (base_path / file_path).resolve()

    # Prevent directory traversal
    if not full_path.is_relative_to(base_path):
        raise ValueError("Path outside repository")

    # Read file
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise ValueError(f"File not found: {file_path}")
    except PermissionError:
        raise ValueError(f"Permission denied: {file_path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

def write_file_atomic(org_id: str, file_path: str, content: str):
    """Atomic file write"""
    base_path = Path(f"/home/orgs/{org_id}/repo").resolve()
    full_path = (base_path / file_path).resolve()

    if not full_path.is_relative_to(base_path):
        raise ValueError("Path outside repository")

    # Ensure parent directory exists
    full_path.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write: temp file → rename
    temp_path = full_path.with_suffix(full_path.suffix + ".tmp")
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
        temp_path.replace(full_path)  # Atomic on same filesystem
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise ValueError(f"Error writing file: {str(e)}")
```

### Alternatives Considered

- **aiofiles**: Adds dependency, async overhead not needed for small file operations
- **Direct writes**: Risk of corruption on failure; atomic pattern is safer
- **No path validation**: Security risk; must validate to prevent directory traversal

## 5. Search Implementation

### Decision

Use **Python's built-in file reading with regex** for server-side search:
- **Approach**: Server-side search (client sends query, server searches files)
- **Implementation**: Standard file I/O + `re.finditer` for regex matching
- **Concurrency**: Use `concurrent.futures.ThreadPoolExecutor` for parallel file scanning
- **Results**: Return all results in single response (no pagination for MVP)
- **Performance**: Acceptable for up to 500 files, 10,000 total lines

### Rationale

- **Server-side**: Client doesn't have filesystem access; server has direct file access
- **Built-in regex**: Fast enough for typical code searches, no external dependencies
- **ThreadPoolExecutor**: Simple parallelism for I/O-bound file reading
- **Single response**: Simpler than streaming; typical code searches return <1000 results
- **No caching**: Search is fast enough without it; caching adds complexity

### Implementation Pattern

```python
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

def search_files(org_id: str, query: str, case_sensitive: bool = False) -> list:
    """Search all files in workspace"""
    base_path = Path(f"/home/orgs/{org_id}/repo")
    flags = 0 if case_sensitive else re.IGNORECASE
    pattern = re.compile(re.escape(query), flags)

    results = []

    def search_file(file_path: Path):
        file_results = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line_num, line in enumerate(lines, 1):
                    for match in pattern.finditer(line):
                        file_results.append({
                            'filePath': str(file_path.relative_to(base_path)),
                            'line': line_num,
                            'column': match.start(),
                            'matchText': match.group(),
                            'contextBefore': lines[line_num - 2].rstrip() if line_num > 1 else None,
                            'contextAfter': lines[line_num].rstrip() if line_num < len(lines) else None
                        })
        except Exception:
            pass  # Skip files that can't be read
        return file_results

    # Parallel search across files
    files = list(base_path.rglob("*"))
    files = [f for f in files if f.is_file()]

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(search_file, f): f for f in files}
        for future in as_completed(futures):
            results.extend(future.result())

    return results
```

### Alternatives Considered

- **ripgrep (rg)**: Fastest option but requires external binary, shell execution complexity
- **Whoosh/Elasticsearch**: Overkill for code search, requires indexing infrastructure
- **asyncio**: ThreadPoolExecutor simpler and more appropriate for I/O-bound tasks
- **Client-side search**: Not viable (no filesystem access in browser)

## Summary

All technical decisions align with simplified architecture and existing infrastructure:

1. ✅ Monaco Editor via official React wrapper (CDN-hosted)
2. ✅ Pragmatic drag and drop for file tree DnD (per user requirement)
3. ✅ Use existing workflow execution endpoints (sync returns results, async shows link)
4. ✅ Standard Python file I/O (no aiofiles needed)
5. ✅ Built-in regex search with ThreadPoolExecutor parallelism

**Key Simplifications**:
- ❌ No workspace session locking (not needed for MVP)
- ❌ No SSE or polling (sync workflows return directly)
- ❌ No Table Storage entities (everything in Azure File Share or existing infrastructure)
- ❌ No new execution infrastructure (reuse existing workflow engine)
- ❌ No Git integration (separate feature for later)

**Next Step**: Proceed to Phase 1 to generate data-model.md and API contracts based on these decisions.
