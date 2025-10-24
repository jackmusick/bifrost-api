# Feature Specification: Browser-Based Code Editor

**Feature Branch**: `008-in-our-application`
**Created**: 2025-10-23
**Status**: Draft
**Input**: User description: "In our application, users will have access to '/home', almost always mounted as a Azure File Share in Azure Functions. We need to create a full screen, VS Code-like editor..."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - File Browsing and Basic Editing (Priority: P1)

A developer opens the editor for the first time, browses through their project files in the `/home/repo` directory, selects a Python file, and makes a quick edit to fix a bug. The file is automatically saved after 5 seconds of inactivity.

**Why this priority**: This is the core MVP - without the ability to browse, open, and edit files, no other features are useful. This story delivers immediate value by allowing developers to make quick edits without needing to set up a local development environment.

**Independent Test**: Can be fully tested by creating test files in `/home/repo`, opening the editor, navigating the file tree, opening a file, making edits, and verifying auto-save occurs after 5 seconds of inactivity. Delivers the core value of browser-based editing.

**Acceptance Scenarios**:

1. **Given** the editor is opened for the first time, **When** the interface loads, **Then** `/home/repo` directory is automatically created if it doesn't exist and the file tree displays its contents
2. **Given** files and folders exist in `/home/repo`, **When** viewing the file tree, **Then** all files and folders are displayed in a hierarchical tree structure with expand/collapse controls
3. **Given** a file is visible in the file tree, **When** clicking on the file name, **Then** the file opens in the Monaco editor with appropriate syntax highlighting
4. **Given** a file is open in the editor, **When** making changes and waiting 5 seconds without further edits, **Then** the file is automatically saved and a save indicator confirms the operation
5. **Given** a file is open with unsaved changes, **When** manually triggering save, **Then** the file is immediately saved and the unsaved indicator clears

---

### User Story 2 - File and Folder Management (Priority: P2)

A developer needs to reorganize their project structure by creating new folders, moving files between directories, renaming components, and deleting obsolete files - all through intuitive drag-and-drop and context menu operations.

**Why this priority**: File management is essential for maintaining organized code but isn't needed for the initial editing workflow. This story enables developers to fully manage their project structure without command-line access.

**Independent Test**: Can be fully tested by performing file operations (create, rename, move, delete) through the UI and verifying the filesystem reflects these changes. Delivers value by enabling complete project organization through the browser.

**Acceptance Scenarios**:

1. **Given** the file tree is visible, **When** right-clicking on a folder, **Then** a context menu appears with options to create new file, create new folder, rename, and delete
2. **Given** a file or folder is selected, **When** dragging it to another folder in the tree, **Then** the item is moved to the target folder and the tree updates to reflect the new structure
3. **Given** a file is selected via context menu "rename", **When** entering a new name and confirming, **Then** the file is renamed and the tree updates immediately
4. **Given** a file or folder is selected for deletion, **When** confirming the delete action, **Then** the item is permanently removed and the tree updates to reflect the deletion
5. **Given** attempting to perform an invalid operation (e.g., moving a folder into itself), **When** the operation is attempted, **Then** a clear error message is displayed and the operation is prevented

---

### User Story 3 - Content Search Across Files (Priority: P2)

A developer needs to find all occurrences of a specific function name or variable across their entire codebase to understand its usage before making changes.

**Why this priority**: Search is a critical productivity feature but not required for basic editing. This story enables developers to quickly locate code across their project, significantly improving efficiency when working with unfamiliar or large codebases.

**Independent Test**: Can be fully tested by creating test files with known content, performing searches for specific text patterns, and verifying all matches are found and displayed with file paths and line numbers. Delivers value by enabling rapid code discovery.

**Acceptance Scenarios**:

1. **Given** the search panel is opened, **When** entering a search term and executing the search, **Then** all files containing the term are listed with file paths, line numbers, and surrounding context
2. **Given** search results are displayed, **When** clicking on a result, **Then** the corresponding file opens in the editor with the cursor positioned at the matched line
3. **Given** multiple matches exist in a single file, **When** viewing search results, **Then** each match is listed separately with its specific line number and context
4. **Given** a search is in progress, **When** the search completes, **Then** a summary displays the total number of matches found across how many files
5. **Given** no matches are found, **When** the search completes, **Then** a clear message indicates no results were found

---

### User Story 4 - Script and Workflow Execution (Priority: P1)

A developer opens a workflow file, configures input parameters through a familiar form interface, executes the workflow, and monitors real-time logs and results in an integrated terminal - all without leaving the editor.

**Why this priority**: This is critical for the "test against live environment" success criterion. Without execution capability, developers would still need to switch contexts to test their changes, defeating a key value proposition.

**Independent Test**: Can be fully tested by creating a test workflow with defined parameters, executing it through the Run panel, providing inputs via the form, and verifying logs and results appear in the terminal. Delivers immediate value by enabling in-browser testing.

**Acceptance Scenarios**:

1. **Given** the Run panel is opened, **When** a Python script, workflow, or data provider file is selected, **Then** an appropriate execution form is displayed based on the file type
2. **Given** a workflow requires input parameters, **When** the execution form loads, **Then** input fields are displayed matching the workflow's parameter definitions (using existing "Run Workflow" form pattern)
3. **Given** execution parameters are configured, **When** triggering execution, **Then** the workflow runs and a terminal panel opens displaying real-time output
4. **Given** a workflow is executing, **When** context information is available at runtime, **Then** it is displayed in a variables section showing current execution state
5. **Given** execution completes (success or failure), **When** reviewing the terminal, **Then** all logs including standard logger output (not just context.info/context.*) are visible with timestamps
6. **Given** multiple executions occur, **When** viewing the terminal, **Then** each execution's output is clearly separated and identifiable

---

### User Story 5 - Integrated Terminal and Log Monitoring (Priority: P2)

A developer runs multiple workflow tests in sequence, adjusts the terminal size to view more log output, scrolls through execution history to compare results, and references error messages while editing code in a split view.

**Why this priority**: While critical for debugging, the terminal enhances the execution experience but isn't the minimum requirement to run and view results. This story enables efficient debugging workflows.

**Independent Test**: Can be fully tested by running multiple executions, resizing the terminal panel, scrolling through output, and verifying all logs are retained and accessible. Delivers value by providing comprehensive debugging capabilities.

**Acceptance Scenarios**:

1. **Given** the terminal panel is visible, **When** dragging the resize handle, **Then** the terminal height adjusts smoothly and editor content reflows appropriately
2. **Given** multiple workflow executions have occurred, **When** scrolling through terminal output, **Then** all historical logs remain accessible in chronological order
3. **Given** execution output includes errors, **When** viewing the terminal, **Then** error messages are clearly formatted and distinguishable from standard output
4. **Given** long-running execution is in progress, **When** new log lines are generated, **Then** the terminal auto-scrolls to show the latest output
5. **Given** terminal contains extensive output, **When** using the terminal search feature (Ctrl+F style), **Then** matching text is highlighted and the terminal scrolls to show the first match with next/previous navigation

---

### User Story 6 - Workspace Layout and Focus Management (Priority: P3)

A developer is making frequent small edits while testing workflows, so they minimize the editor to a compact corner widget to maximize terminal visibility, then quickly restore the full editor when they need to make changes.

**Why this priority**: This is a nice-to-have UX enhancement that improves workflow efficiency but isn't essential for core editing and testing functionality. This story optimizes the experience for rapid edit-test cycles.

**Independent Test**: Can be fully tested by toggling the editor between full-screen and minimized states, verifying the minimized state docks to bottom-right corner, and confirming functionality is preserved in both states. Delivers value by optimizing screen real estate.

**Acceptance Scenarios**:

1. **Given** the editor is in full-screen mode, **When** clicking the minimize control, **Then** the editor collapses to a small widget docked to the bottom-right corner of the viewport
2. **Given** the editor is minimized, **When** clicking the restore control on the widget, **Then** the editor expands back to full-screen mode with all previous state (open file, cursor position, unsaved changes) preserved
3. **Given** the editor is minimized, **When** the widget is visible, **Then** it displays the name of the currently open file (if any) and an indicator for unsaved changes
4. **Given** the editor is minimized, **When** attempting to open a file from a notification or external trigger, **Then** the editor automatically restores to full-screen mode and opens the requested file

---

### Edge Cases

- **What happens when a file is modified externally while open in the editor?** The editor should detect the external change and prompt the user to reload or keep their version, preventing silent data loss.
- **What happens when attempting to open a very large file (>10MB)?** The editor should warn the user about potential performance issues and offer to open in read-only mode or abort.
- **What happens when the auto-save operation fails (e.g., permission denied, disk full)?** The editor must display a clear error notification and preserve unsaved content in browser storage to prevent data loss.
- **What happens when a file is deleted while open in the editor?** The editor should detect the deletion and notify the user, offering to save the content to a new location.
- **What happens when dragging a folder into one of its own subfolders?** The operation should be prevented with a clear error message explaining circular references are not allowed.
- **What happens when network connectivity is lost during file operations?** File operations should queue and retry when connectivity is restored, with clear user feedback about offline status.
- **What happens when attempting to execute a script with syntax errors?** The execution should fail gracefully with syntax error details displayed in the terminal.
- **What happens when concurrent users attempt to access the same workspace?** The system should detect the concurrent session and display an error message indicating another session is active, preventing simultaneous access to the same `/home/repo` workspace.
- **What happens when `/home/repo` cannot be created due to permission issues?** The editor should display a clear error message and potentially offer to work with an alternative directory or read-only mode.
- **What happens when terminal output exceeds memory limits (e.g., 100,000 lines)?** The terminal should implement log rotation or truncation with clear indication that older logs have been discarded.

## Requirements *(mandatory)*

### Functional Requirements

#### File System and Navigation
- **FR-001**: System MUST automatically create `/home/repo` directory on editor initialization if it does not exist
- **FR-002**: System MUST display a hierarchical tree view of all files and folders within `/home/repo`
- **FR-003**: System MUST support expanding and collapsing folders in the tree view
- **FR-004**: System MUST allow users to open files by clicking on them in the tree view
- **FR-005**: System MUST display file icons or indicators to distinguish file types in the tree view

#### File Editing
- **FR-006**: System MUST provide a Monaco editor component for editing file contents
- **FR-007**: System MUST automatically detect and apply syntax highlighting based on file extension
- **FR-008**: System MUST display the current syntax language in a status bar and allow manual selection
- **FR-009**: System MUST automatically save file contents after 5 seconds of inactivity when content has changed
- **FR-010**: System MUST provide a manual save option accessible via keyboard shortcut or UI control
- **FR-011**: System MUST display an indicator showing whether the current file has unsaved changes
- **FR-012**: System MUST support editing one file at a time (no tabs or split editors required in MVP)

#### File and Folder Management
- **FR-013**: System MUST provide a context menu (right-click) on files and folders with operations: open, rename, delete
- **FR-014**: System MUST provide a context menu on folders with additional operations: create new file, create new folder
- **FR-015**: System MUST support drag-and-drop to move files and folders within the tree structure
- **FR-016**: System MUST validate all file operations and prevent invalid actions (e.g., circular folder moves)
- **FR-017**: System MUST update the tree view in real-time after file operations complete
- **FR-018**: System MUST prompt for confirmation before deleting files or folders

#### Search Functionality
- **FR-019**: System MUST provide a search panel accessible from the left sidebar
- **FR-020**: System MUST search file contents across all files in `/home/repo` for user-provided text
- **FR-021**: System MUST display search results with file path, line number, and surrounding context for each match
- **FR-022**: System MUST allow users to click on search results to open the file at the matched location
- **FR-023**: System MUST display a summary of total matches found and number of files searched

#### Script Execution
- **FR-024**: System MUST provide a Run panel accessible from the left sidebar
- **FR-025**: System MUST support execution of Python scripts, workflows, and data providers
- **FR-026**: System MUST display an appropriate input form based on the file type being executed
- **FR-027**: System MUST integrate with the existing "Run Workflow" form for workflows and data providers requiring parameters
- **FR-028**: System MUST display execution results and logs in a terminal panel
- **FR-029**: System MUST capture and display both standard logger output and context-based logging (context.info, etc.)
- **FR-030**: System MUST display runtime context information in a variables section during workflow execution

#### Terminal
- **FR-031**: System MUST provide a read-only terminal panel docked to the bottom of the editor
- **FR-032**: System MUST support vertical resizing of the terminal panel via drag handle
- **FR-033**: System MUST display execution logs in chronological order with timestamps
- **FR-034**: System MUST support scrolling through historical execution output
- **FR-035**: System MUST auto-scroll to display new output as it arrives during execution
- **FR-036**: System MUST clearly separate output from different execution runs
- **FR-037**: System MUST provide in-terminal search functionality (Ctrl+F style) to find and highlight text within terminal output
- **FR-038**: System MUST support next/previous navigation through search matches in the terminal

#### Layout and Interface
- **FR-039**: System MUST provide a left sidebar with icon-based navigation for Files, Search, and Run panels
- **FR-040**: System MUST display only one sidebar panel at a time (switching between Files, Search, Run)
- **FR-041**: System MUST provide a status bar at the bottom displaying current file info and syntax language
- **FR-042**: System MUST use a VS Code Dark theme as the default visual style
- **FR-043**: System MUST ensure all UI elements (sidebar, editor, terminal, status bar) are integrated into a unified layout resembling VS Code
- **FR-044**: System MUST provide a minimize control to collapse the editor to a small widget
- **FR-045**: System MUST dock the minimized editor widget to the bottom-right corner of the viewport
- **FR-046**: System MUST provide a restore control on the minimized widget to return to full-screen mode
- **FR-047**: System MUST preserve editor state (open file, cursor position, unsaved changes) when minimizing and restoring

#### Data Persistence
- **FR-048**: System MUST persist all file changes to the `/home` directory (Azure File Share)
- **FR-049**: System MUST reflect file system changes immediately in both the tree view and editor
- **FR-050**: System MUST handle file system errors gracefully with clear user feedback
- **FR-051**: System MUST prevent concurrent access to the same workspace by detecting and rejecting simultaneous sessions

### Key Entities

- **File**: Represents a file in the `/home/repo` directory with attributes: path, name, content, type/extension, last modified timestamp, unsaved changes indicator
- **Folder**: Represents a directory in `/home/repo` with attributes: path, name, child files and folders, expansion state in tree view
- **Search Result**: Represents a match from content search with attributes: file path, line number, matched text, surrounding context lines
- **Execution Run**: Represents a single script/workflow execution with attributes: file executed, start time, end time, status (running/success/failure), input parameters, output logs, runtime context
- **Editor State**: Represents the current editor configuration with attributes: open file, cursor position, unsaved changes, selected syntax language, layout mode (full-screen/minimized)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can open the editor, navigate to a file, make an edit, and have it automatically saved within 30 seconds of first interaction (from page load to confirmed save)
- **SC-002**: Users can locate specific code across their entire project using search and navigate to results in under 10 seconds
- **SC-003**: Developers can execute a workflow with parameters and view the first log output in under 5 seconds from clicking "Run"
- **SC-004**: File tree operations (open, rename, move, delete) complete and reflect in the UI within 2 seconds
- **SC-005**: The editor interface supports workspaces containing at least 500 files without degraded tree view performance
- **SC-006**: 90% of developers can successfully complete their first edit-save-execute cycle without external documentation
- **SC-007**: Terminal displays logs in real-time with less than 500ms latency from log generation to display
- **SC-008**: Auto-save successfully preserves changes 99.9% of the time without data loss
- **SC-009**: Syntax highlighting correctly identifies and colorizes at least 15 common programming languages (Python, JavaScript, TypeScript, JSON, YAML, Markdown, HTML, CSS, SQL, Bash, PowerShell, C#, Java, Go, Rust)
- **SC-010**: Search operations complete and return results within 5 seconds for workspaces containing up to 10,000 lines of code across all files

## Assumptions

1. **File System Access**: The application already has appropriate Azure Function permissions to read/write to the `/home` directory and Azure File Share
2. **Authentication**: Users are already authenticated before accessing the editor - no additional authentication is required within the editor itself
3. **Single User Per Workspace**: Each `/home/repo` workspace is accessed by a single user at a time - real-time collaboration is not required
4. **Monaco Editor License**: The Monaco Editor library can be used within this application's licensing terms
5. **Network Reliability**: The application has reliable network connectivity to Azure services - offline mode is not required for MVP
6. **Browser Compatibility**: Modern evergreen browsers (Chrome, Edge, Firefox, Safari) are the target - legacy browser support is not required
7. **File Size Limits**: Typical code files are under 10MB - specialized handling for very large files is out of scope for MVP
8. **Execution Environment**: The workflow/script execution environment is already configured and accessible via existing APIs - the editor only needs to trigger execution and display results
9. **Terminal Scrollback Limit**: Terminal history is limited to the most recent 10,000 lines to prevent memory issues
10. **Theme Customization**: Only the default VS Code Dark theme is required - user-selectable themes are out of scope for MVP

## Dependencies

- Monaco Editor library for the code editing component
- Existing "Run Workflow" form component for execution parameter input
- Backend API endpoints for file system operations (read, write, create, delete, rename, move)
- Backend API endpoints for workflow/script execution
- Backend API endpoint or mechanism for real-time log streaming
- Azure File Share mounted at `/home` in the Azure Functions environment

## Out of Scope

- Multi-file editing (tabs or split editors)
- Git integration or version control features
- Code intelligence features (autocomplete, IntelliSense, go-to-definition)
- Debugging capabilities (breakpoints, step-through execution)
- Custom theme creation or theme selection
- Multi-user real-time collaboration
- Offline mode or local-only editing
- Extension marketplace or plugin system
- Integrated terminal with command-line access (only read-only log viewer)
- File upload/download functionality (assumes files are managed through the editor only)
- Workspace or project configuration files
- Build or compilation features beyond script execution
