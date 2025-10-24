# Tasks: Browser-Based Code Editor

**Input**: Design documents from `/specs/008-in-our-application/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test-first development per Constitution Principle IV - tests written before implementation

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions
- **Frontend**: `client/src/`
- **Backend**: `api/`
- Tests first, then implementation (TDD per Constitution)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependencies

- [ ] T001 [P] Install frontend dependencies: `@monaco-editor/react`, `@atlaskit/pragmatic-drag-and-drop`, `zustand`
- [ ] T002 [P] Create editor component directory structure in `client/src/components/editor/`
- [ ] T003 [P] Create editor services directory in `client/src/services/`
- [ ] T004 [P] Create editor stores directory in `client/src/stores/`
- [ ] T005 [P] Create editor hooks directory in `client/src/hooks/`
- [ ] T006 [P] Create backend editor functions directory in `api/functions/`
- [ ] T007 [P] Create backend editor shared modules in `api/shared/editor/`
- [ ] T008 [P] Add editor route to frontend router in `client/src/App.tsx` or routing config

**Checkpoint**: Project structure ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Backend Foundation

- [ ] T009 Add editor Pydantic models to `api/shared/models.py`: `FileMetadata`, `FileContentRequest`, `FileContentResponse`
- [ ] T010 [P] Create base file operations module in `api/shared/editor/file_operations.py` with path validation helper
- [ ] T011 [P] Add OpenAPI decorators for editor endpoints in `api/shared/openapi_decorators.py` (if new decorator needed)
- [ ] T012 [P] Create editor layout component in `client/src/components/editor/EditorLayout.tsx` (shell with sidebar, editor area, terminal area)
- [ ] T013 [P] Create sidebar component in `client/src/components/editor/Sidebar.tsx` (icon navigation for Files, Search, Run)
- [ ] T014 [P] Create status bar component in `client/src/components/editor/StatusBar.tsx` (bottom bar shell)
- [ ] T015 Create editor store in `client/src/stores/editorStore.ts` with Zustand (manages open file, cursor position, unsaved changes, layout mode, sidebar panel)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - File Browsing and Basic Editing (Priority: P1) 🎯 MVP

**Goal**: Developers can browse files in `/home/repo`, open files in Monaco editor, edit content, and auto-save after 5 seconds

**Independent Test**: Create test files in `/home/repo`, open editor, navigate file tree, open file, make edits, verify auto-save after 5 seconds

### Tests for User Story 1

**NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T016 [P] [US1] Contract test for GET /api/editor/files in `api/tests/contract/test_editor_api.py`
- [ ] T017 [P] [US1] Contract test for GET /api/editor/files/content in `api/tests/contract/test_editor_api.py`
- [ ] T018 [P] [US1] Contract test for PUT /api/editor/files/content in `api/tests/contract/test_editor_api.py`
- [ ] T019 [P] [US1] Integration test for file listing in `api/tests/integration/test_editor_file_ops.py`
- [ ] T020 [P] [US1] Integration test for file read/write in `api/tests/integration/test_editor_file_ops.py`
- [ ] T021 [P] [US1] React component test for FileTree in `client/src/components/editor/FileTree.test.tsx`
- [ ] T022 [P] [US1] React component test for CodeEditor in `client/src/components/editor/CodeEditor.test.tsx`
- [ ] T023 [US1] E2E test for complete edit workflow in `client/tests/e2e/editor.spec.ts`

### Backend Implementation for User Story 1

- [ ] T024 [P] [US1] Implement list files logic in `api/shared/editor/file_operations.py` (read directory, return FileMetadata list)
- [ ] T025 [P] [US1] Implement read file logic in `api/shared/editor/file_operations.py` (read file with path validation, return content)
- [ ] T026 [P] [US1] Implement write file logic in `api/shared/editor/file_operations.py` (atomic write with temp file → rename)
- [ ] T027 [US1] Create GET /api/editor/files endpoint in `api/functions/editor_files.py` (list directory)
- [ ] T028 [US1] Create GET /api/editor/files/content endpoint in `api/functions/editor_files.py` (read file)
- [ ] T029 [US1] Create PUT /api/editor/files/content endpoint in `api/functions/editor_files.py` (write file)
- [ ] T030 [US1] Add org-scoped path handling (e.g., `/home/orgs/{org_id}/repo/`) in file_operations.py
- [ ] T031 [US1] Add error handling for permission denied, file not found, path traversal attempts

### Frontend Implementation for User Story 1

- [ ] T032 [P] [US1] Create file service in `client/src/services/fileService.ts` (API client for file operations)
- [ ] T033 [P] [US1] Create FileTree component in `client/src/components/editor/FileTree.tsx` (hierarchical tree, expand/collapse)
- [ ] T034 [US1] Add file tree state management hook in `client/src/hooks/useFileTree.ts` (load files, expand/collapse state)
- [ ] T035 [US1] Create CodeEditor component in `client/src/components/editor/CodeEditor.tsx` (Monaco editor wrapper)
- [ ] T036 [US1] Configure Monaco editor options (syntax highlighting, theme vs-dark, minimap control)
- [ ] T037 [US1] Implement auto-save hook in `client/src/hooks/useAutoSave.ts` (5-second debounce, only if content changed)
- [ ] T038 [US1] Add manual save handler (Ctrl+S / Cmd+S) in CodeEditor component
- [ ] T039 [US1] Add unsaved changes indicator to status bar
- [ ] T040 [US1] Wire FileTree click handler to open file in CodeEditor (update editorStore)
- [ ] T041 [US1] Integrate all US1 components into EditorLayout

**Checkpoint**: At this point, User Story 1 should be fully functional - browse files, edit, auto-save

---

## Phase 4: User Story 4 - Script and Workflow Execution (Priority: P1)

**Goal**: Developers can execute workflows/scripts from the editor and see results/logs in integrated terminal

**Independent Test**: Create test workflow, execute via Run panel, provide parameters, verify logs appear in terminal

**Note**: US4 is P1 priority alongside US1 for MVP

### Tests for User Story 4

- [ ] T042 [P] [US4] Integration test for workflow execution integration in `api/tests/integration/test_editor_execution.py` (verify calls to existing workflow endpoint)
- [ ] T043 [P] [US4] React component test for RunPanel in `client/src/components/editor/RunPanel.test.tsx`
- [ ] T044 [P] [US4] React component test for Terminal in `client/src/components/editor/Terminal.test.tsx`
- [ ] T045 [US4] E2E test for workflow execution in `client/tests/e2e/editor.spec.ts`

### Backend Implementation for User Story 4

- [ ] T046 [US4] Identify existing workflow execution endpoint (e.g., `/api/workflows/execute`) - document in quickstart.md
- [ ] T047 [US4] Document request/response format for sync vs async workflows (for frontend integration)
- [ ] T048 [US4] Add helper in `api/shared/editor/` to format execution response for terminal display (if needed)

### Frontend Implementation for User Story 4

- [ ] T049 [P] [US4] Create workflow service in `client/src/services/workflowService.ts` (wrapper for existing workflow execution API)
- [ ] T050 [P] [US4] Create terminal store in `client/src/stores/terminalStore.ts` (manages logs, execution history)
- [ ] T051 [P] [US4] Create RunPanel component in `client/src/components/editor/RunPanel.tsx` (file selector, parameter form using existing "Run Workflow" form pattern)
- [ ] T052 [US4] Create Terminal component in `client/src/components/editor/Terminal.tsx` (read-only, displays logs with timestamps)
- [ ] T053 [US4] Implement log formatting in Terminal (INFO/WARNING/ERROR color coding, timestamps)
- [ ] T054 [US4] Add sync workflow handler (display logs in terminal)
- [ ] T055 [US4] Add async workflow handler (display message with link + refresh button)
- [ ] T056 [US4] Add execution separator in terminal (clearly separate multiple runs)
- [ ] T057 [US4] Wire RunPanel execute button to workflowService
- [ ] T058 [US4] Integrate RunPanel and Terminal into EditorLayout

**Checkpoint**: User Story 4 complete - execute workflows, view logs

---

## Phase 5: User Story 2 - File and Folder Management (Priority: P2)

**Goal**: Developers can create, rename, move, delete files/folders via context menus and drag-and-drop

**Independent Test**: Perform file operations (create, rename, move, delete) via UI, verify filesystem reflects changes

### Tests for User Story 2

- [ ] T059 [P] [US2] Contract test for POST /api/editor/files (create) in `api/tests/contract/test_editor_api.py`
- [ ] T060 [P] [US2] Contract test for POST /api/editor/files/delete in `api/tests/contract/test_editor_api.py`
- [ ] T061 [P] [US2] Contract test for POST /api/editor/files/rename in `api/tests/contract/test_editor_api.py`
- [ ] T062 [P] [US2] Contract test for POST /api/editor/files/move in `api/tests/contract/test_editor_api.py`
- [ ] T063 [P] [US2] Integration test for file management operations in `api/tests/integration/test_editor_file_ops.py`
- [ ] T064 [P] [US2] React component test for context menu in `client/src/components/shared/ContextMenu.test.tsx`
- [ ] T065 [US2] E2E test for drag-and-drop file move in `client/tests/e2e/editor.spec.ts`

### Backend Implementation for User Story 2

- [ ] T066 [P] [US2] Implement create file/folder logic in `api/shared/editor/file_operations.py`
- [ ] T067 [P] [US2] Implement delete file/folder logic in `api/shared/editor/file_operations.py`
- [ ] T068 [P] [US2] Implement rename file/folder logic in `api/shared/editor/file_operations.py`
- [ ] T069 [P] [US2] Implement move file/folder logic in `api/shared/editor/file_operations.py` with circular reference detection
- [ ] T070 [US2] Create POST /api/editor/files endpoint in `api/functions/editor_files.py` (create file/folder)
- [ ] T071 [US2] Create POST /api/editor/files/delete endpoint in `api/functions/editor_files.py`
- [ ] T072 [US2] Create POST /api/editor/files/rename endpoint in `api/functions/editor_files.py`
- [ ] T073 [US2] Create POST /api/editor/files/move endpoint in `api/functions/editor_files.py`
- [ ] T074 [US2] Add validation for circular folder moves, empty folder deletion

### Frontend Implementation for User Story 2

- [ ] T075 [P] [US2] Create ContextMenu component in `client/src/components/shared/ContextMenu.tsx` (right-click menu with create/rename/delete options)
- [ ] T076 [US2] Integrate Pragmatic drag-and-drop in FileTree component (make items draggable and droppable)
- [ ] T077 [US2] Add context menu handlers to FileTree (create file, create folder, rename, delete)
- [ ] T078 [US2] Implement drag-and-drop move handler in FileTree (call move API, update tree)
- [ ] T079 [US2] Add confirmation dialog for delete operations
- [ ] T080 [US2] Add rename inline edit or modal in FileTree
- [ ] T081 [US2] Add error handling and user feedback for invalid operations (e.g., circular move)
- [ ] T082 [US2] Update fileService with create/delete/rename/move methods

**Checkpoint**: User Story 2 complete - full file management capabilities

---

## Phase 6: User Story 3 - Content Search Across Files (Priority: P2)

**Goal**: Developers can search file contents across entire workspace and navigate to results

**Independent Test**: Create test files with known content, search for text, verify all matches found with file paths and line numbers

### Tests for User Story 3

- [ ] T083 [P] [US3] Contract test for POST /api/editor/search in `api/tests/contract/test_editor_api.py`
- [ ] T084 [P] [US3] Integration test for search functionality in `api/tests/integration/test_editor_search.py` (test regex, case sensitivity, context lines)
- [ ] T085 [P] [US3] React component test for SearchPanel in `client/src/components/editor/SearchPanel.test.tsx`
- [ ] T086 [US3] E2E test for search workflow in `client/tests/e2e/editor.spec.ts`

### Backend Implementation for User Story 3

- [ ] T087 [US3] Add search Pydantic models to `api/shared/models.py`: `SearchRequest`, `SearchResult`, `SearchResponse`
- [ ] T088 [US3] Implement search logic in `api/shared/editor/search.py` (parallel file scanning with ThreadPoolExecutor, regex matching, context lines)
- [ ] T089 [US3] Add case-sensitive and regex support to search
- [ ] T090 [US3] Create POST /api/editor/search endpoint in `api/functions/editor_search.py`
- [ ] T091 [US3] Add search result formatting (file path, line number, match text, context before/after)

### Frontend Implementation for User Story 3

- [ ] T092 [P] [US3] Create search service in `client/src/services/searchService.ts`
- [ ] T093 [US3] Create SearchPanel component in `client/src/components/editor/SearchPanel.tsx` (search input, options, results list)
- [ ] T094 [US3] Add search result item component (displays file path, line, context with highlighting)
- [ ] T095 [US3] Implement search result click handler (open file at specific line in CodeEditor)
- [ ] T096 [US3] Add case-sensitive and regex toggle options
- [ ] T097 [US3] Add search progress indicator and result count summary
- [ ] T098 [US3] Integrate SearchPanel into Sidebar navigation

**Checkpoint**: User Story 3 complete - full-text search functional

---

## Phase 7: User Story 5 - Integrated Terminal and Log Monitoring (Priority: P2)

**Goal**: Developers can resize terminal, scroll through logs, search within terminal output

**Independent Test**: Run multiple executions, resize terminal, scroll output, verify all logs accessible, test in-terminal search

### Tests for User Story 5

- [ ] T099 [P] [US5] React component test for resizable terminal in `client/src/components/editor/Terminal.test.tsx`
- [ ] T100 [P] [US5] React component test for ResizablePanel in `client/src/components/shared/ResizablePanel.test.tsx`
- [ ] T101 [US5] E2E test for terminal resize and search in `client/tests/e2e/editor.spec.ts`

### Frontend Implementation for User Story 5

- [ ] T102 [P] [US5] Create ResizablePanel component in `client/src/components/shared/ResizablePanel.tsx` (drag handle for vertical resize)
- [ ] T103 [US5] Add resize functionality to Terminal component (integrate ResizablePanel)
- [ ] T104 [US5] Implement terminal scrollback buffer (10,000 lines max with truncation)
- [ ] T105 [US5] Add auto-scroll on new logs (with manual scroll detection to pause auto-scroll)
- [ ] T106 [US5] Implement in-terminal search (Ctrl+F style) with text highlighting
- [ ] T107 [US5] Add next/previous navigation for terminal search matches
- [ ] T108 [US5] Add log level formatting (different colors for INFO/WARNING/ERROR)
- [ ] T109 [US5] Ensure execution separator is visually distinct

**Checkpoint**: User Story 5 complete - enhanced terminal capabilities

---

## Phase 8: User Story 6 - Workspace Layout and Focus Management (Priority: P3)

**Goal**: Developers can minimize/restore editor to optimize screen space during rapid edit-test cycles

**Independent Test**: Toggle between full-screen and minimized states, verify state preservation (open file, cursor position, unsaved changes)

### Tests for User Story 6

- [ ] T110 [P] [US6] React component test for EditorLayout minimize/restore in `client/src/components/editor/EditorLayout.test.tsx`
- [ ] T111 [US6] E2E test for minimize/restore workflow in `client/tests/e2e/editor.spec.ts`

### Frontend Implementation for User Story 6

- [ ] T112 [US6] Add minimize button to EditorLayout
- [ ] T113 [US6] Add minimized widget component (bottom-right corner docked)
- [ ] T114 [US6] Implement minimize transition (collapse to widget)
- [ ] T115 [US6] Implement restore transition (expand from widget)
- [ ] T116 [US6] Add layoutMode state to editorStore (fullscreen vs minimized)
- [ ] T117 [US6] Display current file name and unsaved indicator in minimized widget
- [ ] T118 [US6] Add restore control to widget
- [ ] T119 [US6] Ensure editor state is preserved across minimize/restore (open file, cursor position, unsaved changes)
- [ ] T120 [US6] Add auto-restore when file needs to be opened from external trigger

**Checkpoint**: User Story 6 complete - minimize/restore functionality

---

## Phase 9: Polish & Integration

**Purpose**: Cross-cutting concerns and final integration

- [ ] T121 [P] Add loading states for all async operations (file load, search, execution)
- [ ] T122 [P] Add error boundaries for React components
- [ ] T123 [P] Implement offline detection and queue file operations
- [ ] T124 [P] Add external file modification detection (ETag checking on file open)
- [ ] T125 [P] Add large file warning (>10MB) with read-only mode option
- [ ] T126 [P] Add permission error handling with clear user messages
- [ ] T127 [P] Implement browser storage backup for unsaved content (prevent data loss on crashes)
- [ ] T128 [P] Add keyboard shortcuts documentation/help modal
- [ ] T129 [P] Optimize file tree rendering for 500+ files (virtual scrolling if needed)
- [ ] T130 Run full test suite (`cd api && ./test.sh`)
- [ ] T131 Run frontend tests (`cd client && npm test`)
- [ ] T132 Run E2E tests (`cd client && npm run test:e2e`)
- [ ] T133 Run linting (`cd api && ruff check .` and `cd client && npm run lint`)
- [ ] T134 Run type checking (`cd api && npx pyright` and `cd client && npm run tsc`)
- [ ] T135 Generate TypeScript types from API (`cd client && npm run generate:types`)
- [ ] T136 Update quickstart.md with final setup instructions
- [ ] T137 Performance testing (500 files, 10,000 line search, multiple executions)

**Final Checkpoint**: Feature complete, all tests passing, ready for production

---

## Dependency Graph

```
Phase 1 (Setup)
  ↓
Phase 2 (Foundational) ← MUST COMPLETE BEFORE ANY USER STORIES
  ↓
  ├─→ Phase 3 (US1: File Browsing & Editing) [P1] 🎯 MVP ────┐
  ├─→ Phase 4 (US4: Workflow Execution) [P1] 🎯 MVP ─────────┤
  │                                                            ├─→ MVP DELIVERY
  │   (US1 + US4 = Minimum Viable Product)                    │
  │                                                            │
  ├─→ Phase 5 (US2: File Management) [P2] ──────────────────┐│
  ├─→ Phase 6 (US3: Content Search) [P2] ────────────────────┤│
  ├─→ Phase 7 (US5: Terminal Enhancements) [P2] ─────────────┤│
  └─→ Phase 8 (US6: Minimize/Restore) [P3] ──────────────────┘│
                                                                │
Phase 9 (Polish & Integration) ←──────────────────────────────┘
```

**Notes**:
- Phases 3 and 4 can be developed in parallel after Phase 2
- Phases 5, 6, 7 can be developed in parallel after MVP
- Phase 8 can be developed independently after Phase 2
- Each user story is independently testable

---

## Parallel Execution Examples

### Phase 2 (Foundational)
```bash
# Backend foundation tasks can run in parallel
T009 (models) || T010 (file ops) || T011 (decorators)

# Frontend foundation tasks can run in parallel
T012 (layout) || T013 (sidebar) || T014 (status bar)

# Then sequential
T015 (store) → depends on layout/sidebar integration
```

### Phase 3 (US1: MVP)
```bash
# Tests can all run in parallel
T016 || T017 || T018 || T019 || T020 || T021 || T022

# Backend file ops can run in parallel
T024 (list) || T025 (read) || T026 (write)

# Frontend components can run in parallel
T032 (service) || T033 (FileTree) || T035 (CodeEditor) || T036 (Monaco config)
```

### Phases 5-8 (User Stories 2, 3, 5, 6)
```bash
# All P2 stories can be worked on in parallel
Phase 5 (US2) || Phase 6 (US3) || Phase 7 (US5)

# P3 story can start anytime after Phase 2
Phase 8 (US6)
```

---

## Implementation Strategy

### MVP Scope (Deliver First)
**User Story 1** (File Browsing & Editing) + **User Story 4** (Workflow Execution)
- **Tasks**: T001-T041 (Setup + Foundational + US1) + T042-T058 (US4)
- **Value**: Core browser-based editing + testing workflows
- **Timeline**: ~60% of implementation effort
- **Deliverable**: Developers can edit files and test workflows in browser

### Incremental Deliveries
1. **MVP**: US1 + US4 (browse, edit, auto-save, execute workflows)
2. **Enhancement 1**: US2 (file management via UI)
3. **Enhancement 2**: US3 + US5 (search + terminal enhancements)
4. **Polish**: US6 (minimize/restore) + Phase 9 (final polish)

### Independent Testing Criteria

- **US1**: Create files → Open editor → Browse tree → Open file → Edit → Verify auto-save
- **US2**: Right-click folder → Create file → Drag to move → Rename → Delete → Verify all operations
- **US3**: Create files with known text → Search → Verify results → Click result → Verify file opens at line
- **US4**: Select workflow → Enter params → Execute → Verify logs in terminal
- **US5**: Run multiple workflows → Resize terminal → Scroll logs → Search terminal → Verify all work
- **US6**: Minimize editor → Verify widget shows file → Restore → Verify state preserved

---

## Summary

**Total Tasks**: 137
- Setup: 8 tasks
- Foundational: 7 tasks (CRITICAL - blocks all user stories)
- User Story 1 (P1): 26 tasks (MVP)
- User Story 4 (P1): 17 tasks (MVP)
- User Story 2 (P2): 24 tasks
- User Story 3 (P2): 16 tasks
- User Story 5 (P2): 11 tasks
- User Story 6 (P3): 11 tasks
- Polish & Integration: 17 tasks

**Parallel Opportunities**: 62 tasks marked [P] can run in parallel

**MVP Tasks**: T001-T058 (58 tasks = 42% of total)

**Test Tasks**: 28 tasks (per Constitution Principle IV - test-first development)

**Suggested Delivery**:
1. Phase 1-2: Setup + Foundational (1-2 days)
2. Phase 3-4: MVP - US1 + US4 (3-5 days) → **First Release**
3. Phase 5: US2 File Management (2-3 days)
4. Phase 6-7: US3 + US5 Search & Terminal (2-3 days)
5. Phase 8-9: US6 + Polish (1-2 days)

**Total Estimated Effort**: 9-15 days for full feature (2-3 days for MVP)
