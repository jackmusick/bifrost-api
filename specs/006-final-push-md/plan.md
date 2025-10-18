# Implementation Plan: Platform Enhancement Suite - Final Push

**Branch**: `006-final-push-md` | **Date**: 2025-10-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-final-push-md/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This feature suite enhances the Bifrost Integrations platform with 10 major capabilities across forms, workflows, authentication, and user experience. The primary requirements include:

1. **Enhanced Forms**: Dynamic context system with workflow execution on launch, query parameter access, JavaScript-based field visibility, and rich component library (HTML, markdown, date/time, radio, file uploads)
2. **Workflow HTTP API**: Key-based authentication allowing external systems to trigger workflows with global or per-workflow API keys
3. **Async Workflow Execution**: Non-blocking workflow execution with status polling and automatic UI updates
4. **CRON Scheduling**: Time-based workflow triggers with human-readable schedule display
5. **Enhanced Search**: Full-text filtering across all pages with automatic scope-based reloading
6. **Platform Branding**: Custom logo uploads and primary color theming
7. **Advanced Execution Logs**: Efficient indexing for searching millions of execution records
8. **System Workspace**: Built-in workflows and shared utilities for platform examples
9. **Enhanced Authentication**: Entra ID user ID matching to prevent duplicate accounts
10. **Frontend Polish**: Pagination, search, and automatic data loading across all pages

**Technical Approach**: This is primarily a full-stack enhancement leveraging existing Azure Functions backend (Python 3.11) and React frontend (TypeScript). The implementation will extend current Table Storage patterns for new entities (workflow keys, async execution queue, CRON schedules, branding settings), add new Azure Blob Storage integration for file uploads and logos, enhance existing form builder UI with new components and context system, implement worker patterns for async execution, and add authentication flow improvements for Entra ID matching.

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 4.9+ (frontend)
**Primary Dependencies**:
  - Backend: azure-functions, azure-data-tables, azure-storage-blob, cryptography, pydantic, croniter
  - Frontend: React 18+, react-hook-form, react-dropzone, dompurify, expr-eval (or jexl), markdown-it (or react-markdown)

**Storage**: Azure Table Storage (entities), Azure Blob Storage (file uploads, logos, execution results)
**Testing**: pytest, pytest-asyncio (backend); existing frontend test setup
**Target Platform**: Azure Static Web Apps + Azure Functions (serverless)
**Project Type**: Web application (frontend + backend)
**Performance Goals**:
  - Form context updates: <100ms (client-side reactivity)
  - Workflow HTTP API auth: <200ms p95
  - Async workflow queue: <500ms to return "Queued" status
  - Execution log search: <2s for 1M+ entries
  - File uploads: Support up to 100MB without timeout

**Constraints**:
  - Must maintain backward compatibility with existing forms and workflows
  - Cannot introduce SQL databases (Table Storage only per constitution)
  - CRON scheduling must work within Azure Functions constraints (durable functions or timer triggers)
  - File uploads must handle concurrent uploads and storage quota limits

**Scale/Scope**:
  - Target: 50-200 organizations
  - Forms: 10-100 per organization
  - Workflows: 100-1000 executions per day
  - Execution logs: Millions of entries over time
  - Users: 5-50 MSP technicians + variable external form users

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Azure-First Architecture ✅ PASS

- ✅ All compute uses Azure Functions (Python 3.11 runtime)
- ✅ All storage uses Azure Storage services (Table Storage for entities, Blob Storage for files/logos)
- ✅ Authentication uses existing Azure AD integration
- ✅ No third-party cloud services introduced
- ✅ Local development continues using Azurite

**Notes**: This feature fully complies. New file upload and logo storage will use Azure Blob Storage. Async workflow execution will use Azure Storage Queues or Durable Functions.

### II. Table Storage Only ✅ PASS

- ✅ All new entities use Azure Table Storage:
  - Workflow API keys (WorkflowKeys table)
  - Async execution queue (Executions table with status tracking)
  - CRON schedules (WorkflowSchedules table)
  - Platform branding (Config table with branding keys)
  - Form configurations (existing Forms table extended)
  - Entra ID mappings (Users table extended with EntraUserId field)

- ✅ Large data (file uploads, logos, large execution results) uses Blob Storage with Table Storage references
- ✅ No SQL databases introduced
- ✅ Partition key strategy maintains org-scoped access patterns

**Notes**: This feature fully complies. All persistent data uses Table Storage. Blob Storage is used only for large binary data (files, logos) with URIs stored in Table Storage.

### III. Python Backend Standard ✅ PASS

- ✅ All backend code in Python 3.11 Azure Functions
- ✅ New endpoints follow existing patterns (decorators, Pydantic models)
- ✅ Shared code in `api/shared/` module
- ✅ Type hints for all function signatures
- ✅ Async/await for all I/O operations
- ✅ Pydantic models for all request/response

**Notes**: This feature fully complies. All new backend functionality follows existing Python patterns. New models added to `api/shared/models.py`.

### IV. Test-First Development ⚠️ CONDITIONAL PASS

**Business logic features requiring tests:**
- ✅ Workflow HTTP API key validation (contract + integration tests)
- ✅ Async workflow execution and status tracking (integration tests)
- ✅ CRON schedule parsing and execution (unit + integration tests)
- ✅ Entra ID user matching logic (unit + integration tests)
- ✅ Form context system with field visibility evaluation (integration tests)
- ✅ File upload with size/type validation (contract + integration tests)

**Features where tests are optional (per constitution):**
- UI component styling (markdown, HTML rendering, date picker, radio buttons)
- Search box filtering (simple client-side filter logic)
- Branding logo display and color theming (configuration-based UI changes)
- Pagination (well-established pattern)

**Test plan**: Tests MUST be written first for all business logic (key validation, async execution, CRON parsing, auth matching, context evaluation, file validation). UI components and configuration-based features follow standard patterns and can use manual testing.

### V. Single-MSP Multi-Organization Design ✅ PASS

- ✅ All organization-specific entities use org-scoped partition keys:
  - Form configurations: `PartitionKey = OrgId` or `GLOBAL` for shared forms
  - Execution logs: `PartitionKey = OrgId` (org-scoped queries)
  - Branding: `PartitionKey = OrgId` or `GLOBAL` for platform defaults

- ✅ Global MSP config/secrets use `PartitionKey = "GLOBAL"`:
  - Global workflow API keys: `PartitionKey = "GLOBAL"`
  - System workspace workflows: `PartitionKey = "GLOBAL"`

- ✅ HTTP endpoints validate `X-Organization-Id` header when org context required
- ✅ Permission checks verify user has access to org before processing
- ✅ Organization context loaded once per request and passed through call chain
- ✅ MSP users bypass org restrictions; ORG users require role-based permissions

**Notes**: This feature fully complies. New entities follow existing partition strategy. Workflow HTTP API with global keys runs with global scope (MSP-level permissions). Org-specific features (forms, branding, execution logs) maintain org isolation.

### Constitution Check Summary

**Status**: ✅ **PASSED**

All five principles are satisfied. No violations requiring justification. Test-first development will be applied to business logic features as required.

## Project Structure

### Documentation (this feature)

```
specs/006-final-push-md/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output - Technology decisions and patterns
├── data-model.md        # Phase 1 output - Entity definitions and relationships
├── quickstart.md        # Phase 1 output - Developer setup guide
├── contracts/           # Phase 1 output - API endpoint specifications
│   ├── workflow-keys.yaml      # Workflow HTTP API endpoints
│   ├── async-execution.yaml    # Async workflow endpoints
│   ├── cron-schedules.yaml     # CRON schedule endpoints
│   ├── forms-enhanced.yaml     # Enhanced form endpoints (context, components)
│   ├── file-uploads.yaml       # File upload endpoints
│   ├── branding.yaml           # Platform branding endpoints
│   ├── execution-logs.yaml     # Enhanced execution log endpoints
│   └── authentication.yaml     # Entra ID authentication enhancements
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
# Web application structure (Option 2)
api/
├── functions/                   # HTTP endpoint handlers (thin layer)
│   ├── workflow_keys.py        # NEW: Workflow HTTP API key management
│   ├── async_execution.py      # NEW: Async workflow endpoints
│   ├── cron_schedules.py       # NEW: CRON schedule management
│   ├── forms.py                # MODIFIED: Enhanced with context, new components
│   ├── file_uploads.py         # NEW: File upload handling
│   ├── branding.py             # NEW: Platform branding management
│   ├── execution_logs.py       # MODIFIED: Enhanced search/filtering
│   ├── authentication.py       # MODIFIED: Entra ID matching enhancements
│   └── worker.py               # NEW: Async workflow worker (durable function or timer trigger)
│
├── shared/                      # Business logic, models, utilities
│   ├── models.py               # MODIFIED: Add new Pydantic models
│   │                           # - WorkflowKey, AsyncExecution, CronSchedule
│   │                           # - FormConfig, FileUploadMetadata, BrandingSettings
│   │                           # - EntraIdMapping, ExecutionLogFilter
│   ├── auth/                   # Authentication logic
│   │   ├── workflow_keys.py    # NEW: Key validation and scoping logic
│   │   └── entra_id.py         # MODIFIED: User matching with EntraUserId
│   ├── workflows/              # Workflow execution logic
│   │   ├── async_executor.py   # NEW: Async execution queue management
│   │   └── cron_parser.py      # NEW: CRON expression parsing and scheduling
│   ├── storage/                # Storage utilities
│   │   ├── blob_storage.py     # NEW: Blob Storage helpers for files/logos
│   │   └── table_queries.py    # MODIFIED: Enhanced query patterns for search
│   └── openapi_decorators.py   # MODIFIED: Add @has_workflow_key decorator
│
│   # NOTE: Form context, component validation, and visibility evaluation
│   # are 100% CLIENT-SIDE (React). Backend only stores form configuration
│   # and validates submitted data, not render logic or expressions.
│
└── tests/                       # Unit and integration tests
    ├── contract/               # API contract tests (new endpoints)
    │   ├── test_workflow_keys_api.py
    │   ├── test_async_execution_api.py
    │   ├── test_cron_schedules_api.py
    │   ├── test_forms_enhanced_api.py
    │   ├── test_file_uploads_api.py
    │   └── test_branding_api.py
    ├── integration/            # End-to-end flow tests
    │   ├── test_workflow_http_api.py
    │   ├── test_async_workflow_execution.py
    │   ├── test_form_context_and_visibility.py
    │   ├── test_cron_scheduling.py
    │   └── test_entra_id_matching.py
    └── unit/                   # Isolated function tests
        ├── test_context.py
        ├── test_visibility_eval.py
        ├── test_cron_parser.py
        └── test_entra_id_matching.py

client/
├── src/
│   ├── components/             # Reusable components
│   │   ├── forms/              # MODIFIED/NEW: Enhanced form components
│   │   │   ├── FormContext.tsx          # NEW: Context provider
│   │   │   ├── MarkdownComponent.tsx    # NEW: Text/Markdown display
│   │   │   ├── HTMLComponent.tsx        # NEW: HTML with interpolation
│   │   │   ├── DateTimeComponent.tsx    # NEW: Date/Time picker
│   │   │   ├── RadioComponent.tsx       # NEW: Radio buttons
│   │   │   ├── FileUploadComponent.tsx  # NEW: File upload with validation
│   │   │   └── FieldVisibility.tsx      # NEW: Conditional visibility wrapper
│   │   ├── search/             # NEW: Search and filter components
│   │   │   └── SearchBox.tsx            # NEW: Reusable search box
│   │   └── branding/           # NEW: Branding components
│   │       └── Logo.tsx                 # NEW: Logo display with fallback
│   │
│   ├── pages/                  # Page-level components
│   │   ├── forms/              # MODIFIED: Enhanced form builder and execution
│   │   │   ├── FormBuilder.tsx          # MODIFIED: Add context, new components
│   │   │   └── FormExecute.tsx          # MODIFIED: Context loading, query params
│   │   ├── workflows/          # MODIFIED: Enhanced workflow pages
│   │   │   ├── WorkflowList.tsx         # MODIFIED: Add search, show system workflows
│   │   │   └── WorkflowSettings.tsx     # MODIFIED: Add HTTP API, CRON, async settings
│   │   ├── executions/         # MODIFIED: Enhanced execution history
│   │   │   └── ExecutionHistory.tsx     # MODIFIED: Add search, filters, pagination, auto-refresh
│   │   ├── settings/           # NEW: Settings pages
│   │   │   ├── WorkflowKeys.tsx         # NEW: Global workflow key management
│   │   │   └── Branding.tsx             # NEW: Branding configuration
│   │   └── system/             # NEW: System workspace
│   │       └── SystemWorkflows.tsx      # NEW: System workflow visibility toggle
│   │
│   ├── services/               # API client wrappers
│   │   ├── workflowKeys.ts     # NEW: Workflow key API client
│   │   ├── asyncExecution.ts   # NEW: Async execution API client
│   │   ├── cronSchedules.ts    # NEW: CRON schedule API client
│   │   ├── forms.ts            # MODIFIED: Enhanced form API client
│   │   ├── fileUploads.ts      # NEW: File upload API client
│   │   ├── branding.ts         # NEW: Branding API client
│   │   └── executionLogs.ts    # MODIFIED: Enhanced execution log API client
│   │
│   ├── hooks/                  # Custom React hooks
│   │   ├── useFormContext.ts   # NEW: Form context hook
│   │   ├── useWorkflowPolling.ts # NEW: Auto-refresh hook for async status
│   │   └── useSearch.ts        # NEW: Client-side search hook
│   │
│   └── lib/
│       └── v1.d.ts             # MODIFIED: Auto-generated TypeScript types (run npm run generate:types)
│
└── tests/                      # Frontend tests (optional for UI components)

system_workspace/               # NEW: System workspace folder
├── workflows/                  # Example and test workflows
│   ├── example_form_workflow.py
│   └── test_integration.py
└── utilities/                  # Shared utilities for workflows
    ├── __init__.py
    ├── utils.py                # Exported as `from bifrost import utils`
    └── openapi2python.py       # Exported as `from bifrost import openapi2python`
```

**Structure Decision**: This feature uses the existing web application structure (Option 2: frontend + backend). The backend follows the established Azure Functions v2 pattern with thin HTTP handlers in `api/functions/` delegating to business logic in `api/shared/`. The frontend follows the React pattern with components, pages, services, and hooks. New functionality is added by extending existing modules and creating new ones as needed. The system workspace is a new top-level directory for built-in workflows and shared utilities.

## Key Architecture Clarifications

### 1. Form Context & Visibility - 100% Client-Side

**All form logic happens in the browser for instant reactivity:**
- Form context (workflow results, query params, field values) lives in React state
- Visibility expressions evaluated client-side using safe expression parser (expr-eval/jexl)
- No server round-trips for field show/hide logic
- Backend only stores form configuration as JSON and validates submitted data

**Why**: Sub-100ms UI updates require client-side evaluation. Network latency would make forms feel sluggish.

### 2. File Upload - Upload-First, Submit-After Pattern

**Files upload to Blob Storage BEFORE form submission:**
1. User drags/drops files → FileUploadComponent requests SAS URLs from backend
2. Files upload directly to Azure Blob Storage (user sees progress bars)
3. Blob URIs stored in form state: `context.field.{field_name} = [uri1, uri2, ...]`
4. User completes form and clicks Submit
5. Form submits with blob URIs (not file data) to workflow
6. Workflow receives URIs and can download files from Blob Storage

**Why**: Avoids timeout risk for large files. User sees upload progress immediately. Can retry failed uploads before submitting form.

### 3. HTMLComponent - Generic Context Injection

**HTMLComponent accepts ANY context object, not just form context:**

```typescript
<HTMLComponent
  html="<h1>Hello ${context.field.name}!</h1>"
  context={formContext}  // Form usage
/>

<HTMLComponent
  html="<div>Status: ${status}</div>"
  context={workflowData}  // Workflow usage
/>
```

**Why**: Makes component reusable across forms, workflows, dashboards, etc. Template interpolation works with any data structure.

### 4. Backend Responsibilities for Forms

**Backend does NOT render components or evaluate expressions. Backend only:**
- Stores form configuration (JSON schema) in Table Storage
- Validates submitted form data (types, required fields, file size limits)
- Generates SAS URLs for file uploads
- Executes workflows with submitted data
- Provides API endpoints for CRUD operations on forms

**Why**: Separation of concerns. UI logic belongs in React. Backend handles data persistence and workflow orchestration.

## Complexity Tracking

*Fill ONLY if Constitution Check has violations that must be justified*

No violations detected. All constitution principles are satisfied.
