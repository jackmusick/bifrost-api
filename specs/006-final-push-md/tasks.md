# Tasks: Platform Enhancement Suite - Final Push

**Input**: Design documents from `/specs/006-final-push-md/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 [P] Install and configure project dependencies specified in plan.md
  - Backend: azure-functions, azure-data-tables, azure-storage-blob, cryptography, pydantic, croniter, expr-eval
  - Frontend: React 18+, react-hook-form, react-dropzone, dompurify, expr-eval (or jexl), markdown-it (or react-markdown), tinycolor2
  - Path: `/api/requirements.txt`, `/client/package.json`

- [X] T002 [P] Setup local development environment
  - Configure Azurite for local Azure Storage emulation
  - Setup pytest and pytest-asyncio for backend testing
  - Path: `/docker-compose.yml`, `/api/pyproject.toml`

- [X] T003 [P] Initialize project type generation and validation scripts
  - Setup TypeScript compilation (npm run tsc)
  - Configure ESLint and type checking
  - Path: `/client/tsconfig.json`, `/client/.eslintrc.js`

**Checkpoint**: Setup complete - Foundation work can begin

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Extend Table Storage models in `/api/shared/models.py` **COMPLETE**
  - [X] Add WorkflowKey model (HashedKey, WorkflowId, CreatedBy, LastUsedAt, Revoked) - Lines 858-870
  - [X] Add AsyncExecution model (ExecutionId, WorkflowId, Status, Parameters, Context, Result, Error, timestamps) - Lines 902-916
  - [X] Add CronSchedule model (WorkflowId, CronExpression, Enabled, NextRunAt, LastRunAt) - Lines 921-934
  - [X] Add BrandingSettings model (SquareLogoUrl, RectangleLogoUrl, PrimaryColor) - Lines 961-982
  - [X] Add FileUploadMetadata model (FileUrls, FileNames, FileSizes, FileTypes) - FileUploadRequest/Response added
  - Path: `/api/shared/models.py`

- [X] T005 [P] Configure authentication and key management utilities **COMPLETE**
  - [X] Implement workflow key hashing and validation logic - See `/api/shared/auth/workflow_keys.py`
  - [X] Create @has_workflow_key decorator - See `/api/shared/middleware.py` lines 308-411
  - [X] Add key generation and revocation methods
  - Path: `/api/shared/auth/workflow_keys.py`, `/api/shared/middleware.py`

- [X] T006 [P] Setup Blob Storage integration for file/logo handling
  - Implement blob storage helper methods
  - Configure SAS URL generation for uploads
  - Add blob client initialization and connection
  - Path: `/api/shared/storage/blob_storage.py`

- [X] T007 [P] Extend Users table model with EntraUserId field
  - Add EntraUserId field to User model (nullable initially)
  - Add LastEntraIdSync timestamp field
  - Update user provisioning to store Entra ID
  - Path: `/api/shared/models.py` (lines 301-304)

- [X] T008 Create base error handling and logging infrastructure
  - Define custom exception classes for new features (FileUploadError, WorkflowKeyError, AsyncExecutionError, etc.)
  - Setup logging configuration for async workflows, file uploads
  - Path: `/api/shared/exceptions.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel ✅ **COMPLETE**

---

## Phase 3: User Story 1 - Enhanced Form Builder with Context System (Priority: P1) 🎯 MVP

**Goal**: Create dynamic forms with workflow execution, query parameter access, and context-based field visibility

**Independent Test**: Create a form with a launch workflow, submit with query parameters, verify field visibility changes based on context

### Tests for User Story 1

- [X] T010 [P] [US1] Contract test for enhanced form context in `/api/tests/contract/test_forms_enhanced_api.py`
  - Validate form context object structure
  - Test query parameter injection
  - Test workflow result injection
  - Verify form configuration with launch workflow

- [X] T011 [P] [US1] Integration test for form context system in `/api/tests/integration/test_form_context_and_visibility.py`
  - Test form with launch workflow execution
  - Verify query parameter handling
  - Check context propagation to submitted data

### Implementation for User Story 1

- [X] T012 [P] [US1] Update form models in `/api/shared/models.py`
  - Extend FormConfig model with LaunchWorkflowId field (line 492-493)
  - Add QueryParamConfig for parameter handling (allowedQueryParams, lines 494-495)
  - Add VisibilityExpression field to form field configuration (lines 444-445)

- [X] T013 [P] [US1] Implement form context provider in `/client/src/components/forms/FormContext.tsx`
  - Create React Context for form-wide state
  - Implement query parameter extraction from URL
  - Design workflow result storage after launch execution
  - Implement field value tracking in context.field

- [X] T014 [US1] Create field visibility evaluation logic in `/client/src/components/forms/FieldVisibility.tsx`
  - Implement safe expression parsing using expr-eval library (FormContext.tsx lines 70-90)
  - Design reactive visibility updates with useMemo (FormRenderer.tsx lines 467-470)
  - Integrate with form context for real-time evaluation
  - Add error handling for invalid expressions

- [X] T015 [US1] Modify form execution endpoint in `/api/functions/forms.py`
  - Add launch workflow trigger on form load (execute_form_startup, lines 550-771)
  - Implement context generation with workflow results
  - Validate form submission with context-aware validation (validate_launch_workflow_params, lines 35-88)
  - Add endpoint for form context retrieval

- [X] T016 [US1] Create form builder UI updates in `/client/src/pages/forms/FormBuilder.tsx`
  - Add workflow selection dropdown for form launch (line 55, 188-191)
  - Implement context configuration UI panel
  - Design field visibility condition editor with expression syntax help (FieldConfigDialog.tsx with ExpressionEditor)
  - Add preview mode to test visibility conditions (lines 268-292)

**Checkpoint**: User Story 1 (Enhanced Form Builder) is fully functional and independently testable

---

## Phase 4: User Story 2 - Rich Form Components Library (Priority: P1)

**Goal**: Implement comprehensive input components with advanced features like markdown, HTML interpolation, and file uploads

**Independent Test**: Create a form with all new component types, submit the form, verify data capture and rendering

### Tests for User Story 2

- [X] T020 [P] [US2] Contract test for form components in `/api/tests/contract/test_forms_enhanced_api.py`
  - Validate file upload type restrictions
  - Test file upload multiple/single mode
  - Check HTML component interpolation configuration
  - Verify date/time format validation

- [X] T021 [P] [US2] Integration test for component rendering in `/api/tests/integration/test_form_components.py`
  - Verify file upload workflow with SAS URLs
  - Test file size and type validation
  - Check component data submission format (all rich components tested)

### Implementation for User Story 2

- [X] T022 [P] [US2] Create MarkdownComponent in `/client/src/components/forms/MarkdownComponent.tsx`
  - Implement markdown rendering with markdown-it or react-markdown (FormRenderer.tsx lines 338-364, case 'markdown')
  - Support static content display
  - Add styling for headers, lists, links, code blocks

- [X] T023 [P] [US2] Create HTMLComponent in `/client/src/components/forms/HTMLComponent.tsx`
  - Implement generic context interpolation (works with ANY context object) (FormRenderer.tsx lines 366-399, case 'html')
  - Use DOMPurify for XSS prevention (JsxTemplateRenderer uses DOMPurify)
  - Support ${path.to.property} template syntax (JsxTemplateRenderer.tsx with Babel transform)
  - Make reusable across forms, workflows, dashboards

- [X] T024 [P] [US2] Create DateTimeComponent in `/client/src/components/forms/DateTimeComponent.tsx`
  - Implement date/time picker with accessible UI (FormRenderer.tsx lines 316-336, case 'datetime')
  - Support date-only, time-only, and datetime modes
  - Return ISO format values

- [X] T025 [P] [US2] Create RadioComponent in `/client/src/components/forms/RadioComponent.tsx`
  - Implement radio button group with custom options (FormRenderer.tsx lines 284-314, case 'radio')
  - Integrate with form context for value storage
  - Add styling and accessibility features (RadioGroup from shadcn/ui)

- [X] T026 [P] [US2] Create FileUploadComponent in `/client/src/components/forms/FileUploadComponent.tsx`
  - Implement drag-and-drop file upload (FormRenderer.tsx lines 401-439, case 'file')
  - Add file type validation (multi-select dropdown + custom entry)
  - Support multiple file uploads when enabled
  - Show upload progress bars (can be added in future enhancement)
  - [X] Request SAS URLs from backend before upload - Endpoint created at `/api/forms/{formId}/files/upload-url`
  - Upload directly to Blob Storage (upload-first pattern) - Frontend integration pending
  - Store blob URIs in context.field

- [X] T027 [US2] Implement file upload validation in `/api/functions/file_uploads.py`
  - Create endpoint for SAS URL generation - POST `/api/forms/{formId}/files/upload-url`
  - Configure file type restrictions (BlobStorageService.generate_upload_url)
  - Implement file size limits (up to 100MB enforced)
  - Generate secure blob storage URIs with UUID names
  - Add CORS configuration for app domain only (handled by BlobStorageService)

- [X] T028 [US2] Modify form submission model in `/api/shared/models.py`
  - Add support for multiple file uploads (FileUploadRequest/FileUploadResponse, lines 825-835)
  - Create FileUploadMetadata for tracking uploaded files
  - Update form submission validation for file fields

- [X] T029 [US2] Update form builder UI in `/client/src/pages/forms/FormBuilder.tsx`
  - Add new component type buttons (Markdown, HTML, DateTime, Radio, FileUpload) (FieldConfigDialog.tsx)
  - Configure component-specific options in properties panel (OptionsEditor.tsx for radio/select)
  - Design file upload configuration UI (types, multiple, size limits)
  - Add HTML template editor with context variable hints (ExpressionEditor for expressions)

**Checkpoint**: User Story 2 (Rich Form Components) is fully functional and independently testable ✅ **COMPLETE**

---

## Phase 5: User Story 3 - Workflow HTTP API with Key-Based Authentication (Priority: P1)

**Goal**: Enable external systems to trigger workflows via HTTP without user authentication using API keys

**Independent Test**: Generate a workflow key, make an HTTP request with the key, verify workflow executes with global scope

### Tests for User Story 3

- [X] T030 [P] [US3] Contract test for workflow keys in `/api/tests/contract/test_workflow_keys_api.py`
  - Test global key generation
  - Test workflow-specific key generation
  - Verify key revocation and regeneration
  - Check key scope validation

- [X] T031 [P] [US3] Integration test for HTTP workflow execution in `/api/tests/integration/test_workflow_http_api.py`
  - Test workflow execution with valid global key
  - Test workflow execution with workflow-specific key
  - Verify invalid key rejection
  - Check HTTP access toggle enforcement

### Implementation for User Story 3

- [X] T032 [P] [US3] Implement workflow key generation in `/api/functions/workflow_keys.py`
  - Create endpoint for global key generation
  - Create endpoint for workflow-specific key generation
  - Use cryptographically secure random keys (32 bytes, base64-encoded)
  - Hash keys with SHA-256 before storing
  - Return raw key only once (show to user, then discard)
  - Store hashed key in Config table with appropriate RowKey patterns

- [X] T033 [US3] Implement key validation decorator in `/api/shared/middleware.py`
  - Create @has_workflow_key decorator
  - Hash provided key and query Config table
  - Verify key is not expired/revoked
  - Check key scope (global or workflow-specific)
  - Create global scope context for valid keys
  - Fall back to @authenticated if no API key provided

- [X] T034 [US3] Add key management endpoints in `/api/functions/workflow_keys.py`
  - Endpoint to list all keys (masked, show only last 4 chars)
  - Endpoint to revoke key (set Revoked=true)
  - Support for workflow-specific and global keys

- [X] T035 [US3] Implement workflow HTTP access toggle in `/api/shared/models.py`
  - Add endpointEnabled field to WorkflowMetadata model
  - Add allowedMethods field for HTTP method configuration
  - Add disableGlobalKey flag for key scope restrictions
  - Validate HTTP access before executing via API key in endpoints.py

- [X] T036 [US3] Update static web app config in `/staticwebapp.config.json`
  - Configure authentication for workflow endpoints
  - Add @has_workflow_key decorator to workflow execution endpoints
  - Ensure all other endpoints remain secured with @authenticated

- [X] T037 [US3] Create workflow keys UI in `/client/src/pages/WorkflowKeys.tsx`
  - Display keys (masked) with copy and revoke buttons
  - Show workflow-specific keys list
  - Add "Generate Key" button
  - Show key only once on generation with copy button
  - Add revoke button for each key
  - Display last used timestamp

**Checkpoint**: User Story 3 (Workflow HTTP API) is fully functional and independently testable

---

## Phase 6: User Story 4 - Async Workflow Execution with Status Tracking (Priority: P2)

**Goal**: Enable long-running workflows to execute asynchronously with status polling and automatic UI updates

**Independent Test**: Mark a workflow as async, trigger it, verify UI shows "Queued" status with automatic refresh

### Tests for User Story 4

- [X] T040 [P] [US4] Contract test for async execution in `/api/tests/contract/test_async_execution_api.py`
  - Test async workflow trigger endpoint
  - Verify status retrieval endpoint
  - Check execution result retrieval
  - Validate batch status query

- [ ] T041 [P] [US4] Integration test for async workflow in `/api/tests/integration/test_async_workflow_execution.py`
  - Test full async execution lifecycle (queue → running → completed)
  - Verify context preservation in worker
  - Check failure handling and error logging
  - Test execution result storage

### Implementation for User Story 4

- [X] T042 [P] [US4] Implement async execution queue in `/api/shared/async_executor.py`
  - Create function to enqueue workflow execution
  - Store execution metadata in Executions table with status=PENDING
  - Enqueue message to Azure Storage Queue with execution ID
  - Return execution ID immediately (<500ms)
  - Preserve org scope, user permissions, parameters

- [X] T043 [US4] Create worker function in `/api/functions/worker.py`
  - Implement Azure Functions Queue Trigger for "workflow-executions" queue
  - Load execution context from queue message
  - Update status to RUNNING with timestamp
  - Execute workflow with preserved context
  - Store result via ExecutionLogger (handles large results automatically)
  - Update status to SUCCESS or FAILED with timestamps
  - Handle errors and store error details

- [X] T044 [US4] Add async routing in `/api/functions/workflows.py` and `/api/functions/endpoints.py`
  - Add isAsync field to WorkflowMetadata model
  - Modify workflow execution endpoints to check isAsync flag
  - Route to async queue if isAsync=true, else execute synchronously
  - Return 202 Accepted with execution ID for async workflows

- [ ] T045 [US4] Implement status polling in `/client/src/hooks/useWorkflowPolling.ts`
  - Create hook that polls execution status every 5-10 seconds
  - Accept list of execution IDs to monitor
  - Stop polling when all executions complete/fail
  - Use React state to update execution status in place
  - Avoid full page reload

- [ ] T046 [US4] Update execution history UI in `/client/src/pages/executions/ExecutionHistory.tsx`
  - Display execution status badges (Queued, Running, Completed, Failed)
  - Auto-refresh unfinished executions using useWorkflowPolling hook
  - Show timestamps for queued, started, completed
  - Display error details for failed executions
  - Use React.memo to prevent UI flashing during updates

**Checkpoint**: User Story 4 (Async Workflow Execution) is fully functional and independently testable

---

## Phase 7: User Story 5 - CRON-Scheduled Workflows (Priority: P2)

**Goal**: Enable automatic workflow execution on recurring schedules using CRON expressions

**Independent Test**: Create a workflow with a CRON schedule, wait for trigger time, verify execution logs show automatic run

### Tests for User Story 5

- [ ] T050 [P] [US5] Contract test for CRON schedules in `/api/tests/contract/test_cron_schedules_api.py`
  - Test schedule creation with CRON expression
  - Verify schedule update and deletion
  - Check CRON expression validation
  - Test schedule enable/disable toggle

- [ ] T051 [P] [US5] Integration test for CRON scheduling in `/api/tests/integration/test_cron_scheduling.py`
  - Test CRON parser with various expressions
  - Verify next run time calculation
  - Check automatic workflow execution on schedule
  - Test overlapping schedule handling (queue vs skip)

### Implementation for User Story 5

- [ ] T052 [P] [US5] Implement CRON expression parser in `/api/shared/workflows/cron_parser.py`
  - Install and use croniter library
  - Validate CRON expression syntax
  - Calculate next run time from expression
  - Generate human-readable description (e.g., "Every day at 2:00 AM")
  - Cache descriptions in Schedules table

- [ ] T053 [US5] Create CRON schedule management endpoint in `/api/functions/cron_schedules.py`
  - Create endpoint to add schedule to workflow
  - Store schedule in Schedules table (PartitionKey=GLOBAL, RowKey=schedule:{id})
  - Validate CRON expression on creation
  - Calculate and store NextRunAt timestamp
  - Add endpoints for update, delete, enable/disable

- [ ] T054 [US5] Implement timer trigger function in `/api/functions/worker.py`
  - Create Azure Functions Timer Trigger (runs every 5 minutes)
  - Query Schedules table for due schedules (NextRunAt <= now AND Enabled=true)
  - For each due schedule, enqueue workflow execution (reuse async execution pattern)
  - Update LastRunAt and calculate NextRunAt timestamps
  - Handle overlapping schedules (check if workflow still running)

- [ ] T055 [US5] Add CRON configuration UI in `/client/src/pages/workflows/WorkflowSettings.tsx`
  - Add "Schedule" tab in workflow settings
  - Implement CRON expression editor with syntax help
  - Show human-readable schedule description
  - Display next run time
  - Add enable/disable toggle
  - Show last execution timestamp and status

**Checkpoint**: User Story 5 (CRON-Scheduled Workflows) is fully functional and independently testable

---

## Phase 8: User Story 6 - Enhanced Search and Filtering (Priority: P2)

**Goal**: Add full-text search and automatic reloading across all pages with tables and cards

**Independent Test**: Enter search term on workflows page, verify results filter immediately without page reload

### Implementation for User Story 6

- [ ] T060 [P] [US6] Create reusable SearchBox component in `/client/src/components/search/SearchBox.tsx`
  - Implement debounced text input (300ms delay)
  - Add clear button
  - Show search icon
  - Emit onChange event with search term

- [ ] T061 [P] [US6] Create useSearch hook in `/client/src/hooks/useSearch.ts`
  - Accept data array and search term
  - Implement client-side filtering for small datasets (<1000 items)
  - Use useMemo for performance
  - Support multi-field search (name, description, etc.)

- [ ] T062 [P] [US6] Add search to WorkflowList in `/client/src/pages/workflows/WorkflowList.tsx`
  - Add SearchBox component to page header
  - Integrate useSearch hook
  - Filter workflows by name and description
  - Auto-load data on page entry

- [ ] T063 [P] [US6] Add search to ExecutionHistory in `/client/src/pages/executions/ExecutionHistory.tsx`
  - Add SearchBox with filters (user, workflow, status, date range)
  - Implement server-side search for large datasets
  - Add date range picker
  - Implement pagination with "Load More" button
  - Use continuation tokens for efficient paging

- [ ] T064 [P] [US6] Add search to Forms list in `/client/src/pages/forms/FormList.tsx`
  - Add SearchBox component
  - Integrate useSearch hook for client-side filtering
  - Auto-load data on page entry

- [ ] T065 [US6] Implement scope-based auto-reload in `/client/src/hooks/useAutoReload.ts`
  - Create hook that listens to global scope changes
  - Accept resource type (workflows, forms, executions)
  - Reload scoped resources when scope changes
  - Skip reload for unscoped resources (users, global config)
  - Use React useEffect with scope dependency

**Checkpoint**: User Story 6 (Enhanced Search and Filtering) is fully functional and independently testable

---

## Phase 9: User Story 7 - Platform Branding Customization (Priority: P3)

**Goal**: Allow platform administrators to upload custom logos and change primary color scheme

**Independent Test**: Upload a logo and change primary color, verify changes appear in sidebar and forms

### Tests for User Story 7

- [ ] T070 [P] [US7] Contract test for branding API in `/api/tests/contract/test_branding_api.py`
  - Test branding configuration retrieval
  - Verify logo upload and storage
  - Check primary color validation (hex format)
  - Test fallback to default branding

### Implementation for User Story 7

- [ ] T071 [P] [US7] Implement branding storage in `/api/functions/branding.py`
  - Create endpoint to get branding settings (org-specific or global fallback)
  - Create endpoint to update branding (square logo, rectangle logo, primary color)
  - Store branding in Config table (PartitionKey=OrgId or GLOBAL, RowKey="branding")
  - Store logos in Blob Storage, save URLs in Config table
  - Validate logo file types (PNG, JPG, SVG)
  - Validate file size limits (5MB max)

- [ ] T072 [US7] Create Logo component in `/client/src/components/branding/Logo.tsx`
  - Accept type prop (square or rectangle)
  - Fetch branding settings from API
  - Display custom logo if configured, else default logo
  - Add error handler to fallback to default on load failure
  - Use lazy loading for performance

- [ ] T073 [US7] Implement color theming in `/client/src/lib/branding.ts`
  - Load branding settings on app startup
  - Apply primary color using CSS custom properties (--primary-color)
  - Generate color shades using tinycolor2 (darken for hover, lighten for backgrounds)
  - Set CSS variables on :root element
  - Apply generated colors (--primary-dark, --primary-light, etc.)

- [ ] T074 [US7] Create branding settings UI in `/client/src/pages/settings/Branding.tsx`
  - Add to Settings section under "Branding" tab
  - Implement square logo upload with preview
  - Implement rectangle logo upload with preview
  - Add color picker for primary color
  - Show real-time preview of changes
  - Add save button to persist branding

**Checkpoint**: User Story 7 (Platform Branding) is fully functional and independently testable

---

## Phase 10: User Story 8 - Execution Logs with Advanced Indexing (Priority: P3)

**Goal**: Enable efficient search of execution history with millions of entries using optimized indexing

**Independent Test**: Create 10,000 execution logs, search by workflow and status within date range, verify results return quickly

### Implementation for User Story 8

- [ ] T080 [P] [US8] Optimize execution log RowKey structure in `/api/shared/models.py`
  - Change RowKey format to exec:{reverse_timestamp}:{execution_id}
  - Calculate reverse_timestamp as 9999999999999 - timestamp_ms
  - Enables efficient date range queries (newest first)
  - Update execution creation to use new RowKey format

- [ ] T081 [P] [US8] Create secondary indexes in `/api/shared/storage/table_queries.py`
  - Create user index: userexec:{user_id}:{reverse_timestamp}:{execution_id}
  - Create workflow index: workflowexec:{workflow_id}:{reverse_timestamp}:{execution_id}
  - Create status index: statusexec:{status}:{reverse_timestamp}:{execution_id}
  - Store in Relationships table with PartitionKey=GLOBAL
  - Update on every execution creation

- [ ] T082 [US8] Implement efficient query patterns in `/api/functions/execution_logs.py`
  - Create endpoint for filtered execution queries
  - Support filters: user_id, workflow_id, status, start_date, end_date
  - Use appropriate index based on filters
  - Return 50-100 entries per page with continuation tokens
  - Batch fetch full execution records from primary table

- [ ] T083 [US8] Update execution history UI in `/client/src/pages/executions/ExecutionHistory.tsx`
  - Add advanced filter panel (user, workflow, status, date range)
  - Implement date range picker for time-based filtering
  - Add status filter dropdown (All, Queued, Running, Completed, Failed)
  - Show loading state during filter changes
  - Display result count and applied filters

**Checkpoint**: User Story 8 (Execution Logs with Advanced Indexing) is fully functional and independently testable

---

## Phase 11: User Story 9 - System Workspace with Built-in Workflows (Priority: P3)

**Goal**: Provide system workspace folder with example workflows and shared utilities

**Independent Test**: View system workspace folder, execute a system workflow, verify it runs correctly

### Implementation for User Story 9

- [ ] T090 [P] [US9] Create system workspace directory structure
  - Create `/system_workspace/workflows/` folder
  - Create `/system_workspace/utilities/` folder
  - Add `__init__.py` to utilities folder
  - Path: `/system_workspace/`

- [ ] T091 [P] [US9] Implement shared utilities in `/system_workspace/utilities/utils.py`
  - Create common utility functions (parse_date, format_currency, etc.)
  - Export from __init__.py as `from bifrost import utils`
  - Add type hints for all functions
  - Add docstrings with usage examples

- [ ] T092 [P] [US9] Create example system workflow in `/system_workspace/workflows/example_form_workflow.py`
  - Implement simple workflow demonstrating form data processing
  - Use @workflow decorator
  - Import bifrost utilities
  - Add documentation comments

- [ ] T093 [US9] Implement auto-import mechanism in `/api/functions/startup.py`
  - Scan system_workspace/workflows/ on platform startup
  - Import workflows using importlib
  - Register workflows in Workflows table with IsSystem=true, Visible=false
  - Store workflow metadata (PartitionKey=GLOBAL)

- [ ] T094 [US9] Add system workflow visibility toggle in `/client/src/pages/workflows/WorkflowList.tsx`
  - Add "Show System Workflows" toggle in UI
  - Filter workflow list based on toggle state
  - Display "System" badge on system workflows
  - Prevent editing/deletion of system workflows

**Checkpoint**: User Story 9 (System Workspace) is fully functional and independently testable

---

## Phase 12: User Story 10 - Enhanced Authentication with Entra ID User Matching (Priority: P2)

**Goal**: Match users by Entra ID user ID first, then email, preventing duplicate accounts

**Independent Test**: Change a user's email in Entra ID, log in, verify same account is accessed

### Tests for User Story 10

- [ ] T100 [P] [US10] Unit test for Entra ID matching in `/api/tests/unit/test_entra_id_matching.py`
  - Test matching by EntraUserId (primary)
  - Test email fallback matching
  - Verify email update when EntraUserId matches
  - Test new user creation with EntraUserId

- [ ] T101 [P] [US10] Integration test for authentication in `/api/tests/integration/test_entra_id_matching.py`
  - Test full authentication flow with Entra ID token
  - Verify EntraUserId extraction from JWT
  - Check backfill for existing users
  - Test duplicate account prevention

### Implementation for User Story 10

- [ ] T102 [US10] Implement dual-matching logic in `/api/shared/auth/entra_id.py`
  - Create match_or_create_user function
  - Extract EntraUserId (oid claim) from JWT token
  - Query Users table by EntraUserId first
  - If match found, update email if changed
  - If no match, query by email (migration path)
  - If email match found, backfill EntraUserId
  - If no match found, create new user with EntraUserId

- [ ] T103 [US10] Update authentication endpoint in `/api/functions/authentication.py`
  - Extract oid claim from Azure AD token
  - Call match_or_create_user with EntraUserId and email
  - Log email changes for audit trail
  - Return user with updated information

- [ ] T104 [US10] Add migration script for existing users in `/api/scripts/backfill_entra_ids.py`
  - Query all users with EntraUserId=null
  - For each user, attempt to match with Entra ID during next login
  - Log migration progress
  - Handle edge cases (email collisions, null values)

**Checkpoint**: User Story 10 (Enhanced Authentication) is fully functional and independently testable

---

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T110 [P] Update API documentation in `/api/functions/openapi.py`
  - Document all new endpoints
  - Add request/response examples
  - Update OpenAPI schema

- [ ] T111 [P] Generate TypeScript types in `/client/src/lib/v1.d.ts`
  - Run npm run generate:types with function app running
  - Verify all new models and endpoints are typed
  - Fix any type generation errors

- [ ] T112 [P] Add comprehensive logging across all features
  - Execution logs for workflow HTTP API calls
  - Audit trail for branding changes
  - Performance metrics for async execution
  - Error tracking for file uploads

- [ ] T113 Code cleanup and refactoring
  - Remove dead code
  - Consolidate duplicate logic
  - Improve naming consistency
  - Add code comments for complex logic

- [ ] T114 [P] Security hardening
  - Review XSS prevention in HTMLComponent
  - Validate file upload security (MIME type spoofing)
  - Audit workflow key storage and hashing
  - Check CORS configuration for blob uploads

- [ ] T115 [P] Performance optimization
  - Profile execution log queries
  - Optimize form context re-renders
  - Review blob storage upload performance
  - Add caching for branding settings

- [ ] T116 Run quickstart.md validation
  - Verify all setup steps work
  - Test local development environment
  - Validate all npm/pip commands
  - Check Azure Storage emulation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-12)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed) or sequentially in priority order
  - Suggested MVP: Phase 3 (User Story 1) only
- **Polish (Phase 13)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1) - Enhanced Forms**: Can start after Foundational - No dependencies
- **User Story 2 (P1) - Rich Components**: Can start after Foundational - Independent of US1, but integrates with form context
- **User Story 3 (P1) - Workflow HTTP API**: Can start after Foundational - No dependencies
- **User Story 4 (P2) - Async Execution**: Can start after Foundational - No dependencies
- **User Story 5 (P2) - CRON Scheduling**: Can start after Foundational - May integrate with US4 (async execution)
- **User Story 6 (P2) - Enhanced Search**: Can start after Foundational - Can be added to any completed user story's UI
- **User Story 7 (P3) - Platform Branding**: Can start after Foundational - No dependencies
- **User Story 8 (P3) - Execution Logs**: Can start after Foundational - Benefits from US4 (async logs) but independent
- **User Story 9 (P3) - System Workspace**: Can start after Foundational - No dependencies
- **User Story 10 (P2) - Enhanced Auth**: Can start after Foundational - No dependencies

### Within Each User Story

- Tests MUST be written and FAIL before implementation (for stories with tests)
- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Models within a story marked [P] can run in parallel
- Component implementations within a story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Execution Examples

### Parallel Example: Setup Phase
```bash
# Launch all setup tasks together:
Task: "Install backend dependencies"
Task: "Install frontend dependencies"
Task: "Setup local development environment"
Task: "Initialize type generation scripts"
```

### Parallel Example: Foundational Phase
```bash
# Launch all foundational tasks together:
Task: "Extend Table Storage models"
Task: "Configure authentication utilities"
Task: "Setup Blob Storage integration"
Task: "Extend Users table model"
```

### Parallel Example: User Story 1
```bash
# Launch all tests for User Story 1 together:
Task: "Contract test for enhanced form context"
Task: "Integration test for form context system"

# Launch all models for User Story 1 together:
Task: "Update form models"
Task: "Implement form context provider"
```

### Parallel Example: User Story 2
```bash
# Launch all component implementations together:
Task: "Create MarkdownComponent"
Task: "Create HTMLComponent"
Task: "Create DateTimeComponent"
Task: "Create RadioComponent"
Task: "Create FileUploadComponent"
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2 Only)

This delivers core form enhancement capabilities:

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Enhanced Form Builder with Context)
4. Complete Phase 4: User Story 2 (Rich Form Components)
5. **STOP and VALIDATE**: Test both stories independently
6. Deploy/demo if ready

**MVP Value**: Dynamic forms with context, visibility conditions, rich components, and file uploads. Forms can execute workflows on launch and respond to user input in real-time.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 (HTTP API) → Test independently → Deploy/Demo
5. Add User Story 4 (Async) → Test independently → Deploy/Demo
6. Add User Story 5 (CRON) → Test independently → Deploy/Demo
7. Add User Story 6 (Search) → Test independently → Deploy/Demo
8. Add User Story 7 (Branding) → Test independently → Deploy/Demo
9. Add User Story 8 (Logs) → Test independently → Deploy/Demo
10. Add User Story 9 (System Workspace) → Test independently → Deploy/Demo
11. Add User Story 10 (Enhanced Auth) → Test independently → Deploy/Demo
12. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Enhanced Forms)
   - Developer B: User Story 2 (Rich Components)
   - Developer C: User Story 3 (Workflow HTTP API)
   - Developer D: User Story 4 (Async Execution)
3. Stories complete and integrate independently
4. Continue with remaining stories based on priority

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing (TDD approach)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Summary

- **Total Tasks**: 116 tasks across all phases
- **Setup Phase**: 3 tasks
- **Foundational Phase**: 5 tasks (BLOCKING)
- **User Story 1**: 7 tasks (2 tests + 5 implementation)
- **User Story 2**: 10 tasks (2 tests + 8 implementation)
- **User Story 3**: 8 tasks (2 tests + 6 implementation)
- **User Story 4**: 7 tasks (2 tests + 5 implementation)
- **User Story 5**: 6 tasks (2 tests + 4 implementation)
- **User Story 6**: 6 tasks (all implementation, no tests - UI feature)
- **User Story 7**: 4 tasks (1 test + 3 implementation)
- **User Story 8**: 4 tasks (all implementation)
- **User Story 9**: 5 tasks (all implementation)
- **User Story 10**: 5 tasks (2 tests + 3 implementation)
- **Polish Phase**: 7 tasks

**Parallel Opportunities**: 60+ tasks marked [P] for parallel execution
**MVP Scope**: Phases 1-4 (Setup + Foundational + US1 + US2) = 25 tasks
**Independent Test Criteria**: Each user story has clear acceptance criteria from spec.md
