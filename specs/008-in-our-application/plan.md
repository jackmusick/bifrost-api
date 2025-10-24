# Implementation Plan: Browser-Based Code Editor

**Branch**: `008-in-our-application` | **Date**: 2025-10-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-in-our-application/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a full-screen, VS Code-like browser-based code editor that allows developers to browse, edit, search, and execute code files within the `/home/repo` directory (Azure File Share). The editor will provide Monaco-based editing with auto-save, file management via drag-and-drop and context menus, content search across files, integrated workflow/script execution, and a read-only terminal for monitoring logs. This enables developers to make quick edits and test against a live Azure Functions environment without leaving the browser.

**Technical Approach**: React-based frontend with Monaco Editor component, WebSocket/Server-Sent Events for real-time log streaming, RESTful backend APIs for file operations and execution, integration with existing workflow execution infrastructure.

## Technical Context

**Language/Version**: TypeScript 4.9+ (Frontend), Python 3.11 (Backend APIs)
**Primary Dependencies**:
- Frontend: React 18+, @monaco-editor/react, @atlaskit/pragmatic-drag-and-drop, zustand (state management)
- Backend: azure-functions, existing workflow engine
**Storage**: Azure File Share mounted at `/home` in Azure Functions (no Table Storage needed)
**Testing**: Jest + React Testing Library (frontend), pytest + pytest-asyncio (backend integration tests)
**Target Platform**: Modern browsers (Chrome, Edge, Firefox, Safari latest versions)
**Project Type**: Web application (frontend + backend)
**Performance Goals**:
- File tree load: <500ms for 500 files
- File open: <200ms for files <1MB
- Auto-save: <100ms response time
- Search: <5s for 10,000 lines across all files
- Sync workflow execution: <5s for typical workflows
**Constraints**:
- Single file editing (no multi-tab support in MVP)
- File size limit: 10MB per file
- Terminal scrollback: 10,000 lines max per execution
- Async workflows show completion message (not real-time logs)
**Scale/Scope**:
- Target: 50-200 organizations using editor concurrently
- Files per workspace: Up to 500 files
- Execution frequency: 100-1000 runs per day

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Azure-First Architecture ✅ PASS

**Compliance**:
- ✅ Uses Azure Functions for all backend APIs (file operations, execution)
- ✅ Uses Azure File Share for `/home` storage (already mounted)
- ✅ Uses Azure Table Storage for workspace session locks (prevent concurrent access)
- ✅ Uses Azure AD for authentication (inherited from existing platform)
- ✅ Local development uses Azurite

**No violations**: All infrastructure is Azure-native.

### II. Table Storage Only ✅ PASS

**Compliance**:
- ✅ No Table Storage needed for this feature
- ✅ File content stored in Azure File Share (acceptable per principle - files/logs)
- ✅ Execution logs handled by existing infrastructure
- ✅ No SQL database requirements

**Storage breakdown**:
- Azure File Share: File contents at `/home/repo`
- Existing execution infrastructure: Workflow logs and results

**No violations**: No new storage requirements. Uses existing infrastructure.

### III. Python Backend Standard ✅ PASS

**Compliance**:
- ✅ All backend APIs written in Python 3.11
- ✅ Uses Azure Functions v2 programming model
- ✅ Shared code in `api/shared/` modules
- ✅ Type hints for all function signatures
- ✅ Async/await for I/O operations (file system, Table Storage)
- ✅ Pydantic models for all request/response

**Frontend exception**: React/TypeScript for client UI (explicitly permitted)

**No violations**: Backend follows Python standard, frontend is permitted exception.

### IV. Test-First Development ✅ PASS

**Compliance**:
- ✅ Contract tests required for all file operation endpoints
- ✅ Integration tests required for workflow execution flow
- ✅ E2E tests required for file tree operations
- ✅ UI component tests for Monaco editor integration

**Test categories**:
- Contract: `tests/contract/test_editor_api.py` - File operations API contracts
- Integration: `tests/integration/test_editor_file_ops.py` - File system integration
- Integration: `tests/integration/test_editor_execution.py` - Workflow execution integration
- E2E: `client/tests/e2e/test_editor_workflow.spec.ts` - End-to-end user flows

**No violations**: All business logic requires tests per principle.

### V. Single-MSP Multi-Organization Design ✅ PASS

**Compliance**:
- ✅ File operations validate `X-Organization-Id` header
- ✅ MSP users can access any org's workspace (global permission)
- ✅ ORG users restricted to their organization's workspace (role-based)
- ✅ Organization context loaded via existing decorators
- ✅ Execution uses existing org-scoped workflow infrastructure

**Org-scoped patterns**:
- File paths: `/home/orgs/{OrgId}/repo/`
- Permission check: User has `editor:access` permission for OrgId
- Workflow execution: Uses existing org context from workflow engine

**No violations**: Full org-scoping via existing infrastructure.

### Constitution Compliance Summary

**Status**: ✅ ALL PRINCIPLES SATISFIED

**Violations**: None

**Justifications**: N/A - No complexity additions or principle violations

## Project Structure

### Documentation (this feature)

```
specs/008-in-our-application/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── file-operations.openapi.yaml
│   └── search.openapi.yaml
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Frontend (React + TypeScript)
client/
├── src/
│   ├── components/
│   │   ├── editor/
│   │   │   ├── CodeEditor.tsx          # Monaco editor wrapper
│   │   │   ├── FileTree.tsx            # File browser with drag-and-drop
│   │   │   ├── SearchPanel.tsx         # File content search
│   │   │   ├── RunPanel.tsx            # Execution panel with forms
│   │   │   ├── Terminal.tsx            # Read-only terminal with search
│   │   │   ├── StatusBar.tsx           # Bottom status bar
│   │   │   ├── Sidebar.tsx             # Left icon-based sidebar
│   │   │   └── EditorLayout.tsx        # Main layout container
│   │   └── shared/
│   │       ├── ContextMenu.tsx         # Right-click context menu
│   │       └── ResizablePanel.tsx      # Resizable split panels
│   ├── pages/
│   │   └── EditorPage.tsx              # Full-screen editor page
│   ├── services/
│   │   ├── fileService.ts              # File operations API client
│   │   ├── searchService.ts            # Search API client
│   │   └── workflowService.ts          # Uses existing workflow execution API
│   ├── stores/
│   │   ├── editorStore.ts              # Zustand store for editor state
│   │   └── terminalStore.ts            # Zustand store for terminal state
│   └── hooks/
│       ├── useFileTree.ts              # File tree state management
│       └── useAutoSave.ts              # Auto-save debouncing
└── tests/
    └── e2e/
        └── editor.spec.ts              # Playwright E2E tests

# Backend (Python Azure Functions)
api/
├── functions/
│   ├── editor_files.py                 # File operations endpoints
│   └── editor_search.py                # Search endpoints
├── shared/
│   ├── models.py                       # Pydantic models (add Editor models)
│   ├── editor/
│   │   ├── __init__.py
│   │   ├── file_operations.py          # File system operations logic
│   │   └── search.py                   # Search implementation
│   └── openapi_decorators.py           # Existing decorators
└── tests/
    ├── contract/
    │   └── test_editor_api.py          # API contract tests
    ├── integration/
    │   ├── test_editor_file_ops.py     # File operations integration
    │   └── test_editor_execution.py    # Execution integration
    └── e2e/
        └── test_editor_flow.py         # End-to-end Python tests
```

**Structure Decision**: Web application structure (Option 2) selected because this feature requires both a React frontend (Monaco editor, file tree UI) and Python backend (file operations, execution APIs). The frontend lives in `client/src/components/editor/` as a new feature module, and backend lives in `api/functions/editor_*.py` following the existing pattern of one function file per route group.

## Complexity Tracking

*No violations - this section intentionally left empty*

## Phase 0: Research & Technical Decisions

### Research Areas

The following technical decisions require research to determine optimal implementation approaches:

1. **Monaco Editor Integration**
   - How to integrate @monaco-editor/react in our React app
   - Syntax highlighting configuration for 15+ languages
   - Performance optimization for large files
   - Auto-save debouncing strategy

2. **File Tree UI with Drag-and-Drop**
   - Pragmatic drag and drop integration (user-specified)
   - Tree view component library or custom implementation
   - Performance for 500+ file trees
   - Context menu implementation

3. **Workflow Execution Integration**
   - Identify existing workflow execution endpoint
   - Request/response format for synchronous vs async workflows
   - How to display results in terminal (sync) vs link message (async)
   - Integration with existing org context and permissions

4. **File System Operations**
   - Standard Python file I/O patterns for Azure File Share
   - Path validation to prevent directory traversal
   - Error handling for permission denied, disk full scenarios

5. **Search Implementation**
   - Server-side file content search with Python regex
   - Performance for searching 10,000+ lines
   - Parallel file scanning with standard library
   - Search result formatting and context lines

### Research Tasks Dispatched

Research tasks will be generated in `research.md` to answer these questions with specific technical decisions, alternatives considered, and rationale.

## Phase 1: Design Artifacts

Phase 1 will generate the following artifacts after research is complete:

### data-model.md

Will define:
- FileMetadata entity (response model for files/folders)
- FileContent entity (request/response model for file contents)
- SearchResult entity (search response model)
- EditorState entity (frontend UI state - not persisted)

### contracts/

Will contain OpenAPI 3.0 specifications for:

**file-operations.openapi.yaml**:
- GET /api/editor/files - List files in directory
- GET /api/editor/files/content - Read file content
- PUT /api/editor/files/content - Write file content
- POST /api/editor/files - Create new file/folder
- POST /api/editor/files/delete - Delete file/folder
- POST /api/editor/files/rename - Rename file/folder
- POST /api/editor/files/move - Move file/folder

**search.openapi.yaml**:
- POST /api/editor/search - Search file contents (returns all results)

**Note**: Workflow execution uses existing API endpoints - no new contracts needed

### quickstart.md

Will provide:
- Local development setup (Azurite, function app, frontend dev server)
- How to open the editor (/editor route)
- How to test file operations manually
- How to test workflow execution
- How to run integration tests

## Phase 2: Task Generation

Phase 2 (executed via `/speckit.tasks` command - NOT part of this plan) will generate a dependency-ordered task list in `tasks.md` based on the user stories, data model, and contracts defined in this plan.

---

**Plan Status**: Ready for Phase 0 research execution
**Next Command**: Continue with `/speckit.plan` to generate research.md
