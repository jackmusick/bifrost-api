# Feature Specification: Platform Enhancement Suite - Final Push

**Feature Branch**: `006-final-push-md`
**Created**: 2025-10-17
**Status**: Draft
**Input**: User description: "@FINAL PUSH.md"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enhanced Form Builder with Context System (Priority: P1)

Platform users need to create dynamic forms that can execute workflows on form launch, access workflow results, handle query parameters, and show/hide fields based on user input.

**Why this priority**: Forms are the primary user-facing interface for workflow execution. Without context and dynamic visibility, forms are limited to static data collection, severely restricting their usefulness.

**Independent Test**: Can be fully tested by creating a form with a launch workflow, submitting it with query parameters, and verifying that field visibility changes based on selections. Delivers immediate value by enabling dynamic, data-driven forms.

**Acceptance Scenarios**:

1. **Given** a form creator is building a new form, **When** they select a workflow to run on form launch, **Then** the workflow executes automatically when users open the form and results are available in `context.workflow_result`
2. **Given** a form is accessed with query parameters (?foo=bar), **When** the form loads, **Then** those parameters are available in `context.params.foo`
3. **Given** a form has fields with JavaScript visibility conditions, **When** a user changes a field value, **Then** dependent fields show/hide immediately based on the condition
4. **Given** a form creator sets a field visibility to `context.field.first_name !== null`, **When** the user fills in the first_name field, **Then** the dependent field becomes visible
5. **Given** a form includes organizational vs global scope selection, **When** the user switches scopes, **Then** the form context updates to reflect the new scope automatically

---

### User Story 2 - Rich Form Components Library (Priority: P1)

Form creators need a comprehensive set of input components including text/markdown displays, HTML content with variable interpolation, date/time pickers, radio buttons, and file uploads with type restrictions.

**Why this priority**: A limited component library restricts what can be built with forms. Rich components enable complex workflows like document collection, scheduling, and dynamic content display.

**Independent Test**: Can be fully tested by creating a form with each component type, submitting the form, and verifying data is captured correctly. Delivers immediate value by expanding form capabilities.

**Acceptance Scenarios**:

1. **Given** a form includes a Text/Markdown component, **When** users view the form, **Then** the markdown is rendered properly for information display
2. **Given** a form includes an HTML component with `${context.field.first_name}` interpolation, **When** the user enters their name, **Then** the HTML updates to show the name in real-time
3. **Given** a form includes a Date/Time picker, **When** the user selects a date and time, **Then** the value is submitted in ISO format
4. **Given** a form includes a file upload with allowed types (pdf, docx), **When** the user attempts to upload a .exe file, **Then** the upload is rejected with a clear error message
5. **Given** a form has a file upload allowing multiple files, **When** the user uploads 3 files, **Then** all files are uploaded to storage and a list of URIs is sent to the workflow
6. **Given** a form includes radio buttons with 3 options, **When** the user selects an option, **Then** the value is stored in `context.field.[field_name]` and available to other components

---

### User Story 3 - Workflow HTTP API with Key-Based Authentication (Priority: P1)

Platform administrators and external systems need to trigger workflows via HTTP without requiring user authentication, using global or per-workflow API keys.

**Why this priority**: Enables integration with external systems, scheduled jobs, and webhooks. This is essential for automation use cases and makes the platform extensible.

**Independent Test**: Can be fully tested by generating a workflow key, making an HTTP request with the key, and verifying the workflow executes with global scope permissions. Delivers immediate value by enabling API-driven automation.

**Acceptance Scenarios**:

1. **Given** a platform admin is in the settings page, **When** they generate a global workflow key, **Then** the key can be used to trigger any workflow with global scope permissions
2. **Given** a workflow owner is viewing workflow settings, **When** they generate a workflow-specific key, **Then** the key can only trigger that specific workflow
3. **Given** an external system has a workflow key, **When** it makes an HTTP request with `x-workflows-key` header, **Then** the workflow executes without requiring user authentication
4. **Given** a workflow key is compromised, **When** the admin regenerates the key, **Then** the old key is invalidated immediately and requests using it fail
5. **Given** a workflow has HTTP access disabled, **When** a request is made with a valid key, **Then** the request is rejected with an appropriate error message
6. **Given** a workflow is triggered via HTTP with a global key, **When** the workflow executes, **Then** it runs with global scope permissions (like Platform Admin)

---

### User Story 4 - Async Workflow Execution with Status Tracking (Priority: P2)

Users need to trigger long-running workflows asynchronously and check their status without blocking the UI, with automatic status updates every 5-10 seconds.

**Why this priority**: Long-running workflows currently block the UI and timeout. Async execution is essential for scalability and user experience but can be partially mitigated with optimizations.

**Independent Test**: Can be fully tested by marking a workflow as async, triggering it from a form, and verifying the UI shows "Queued" status with automatic refresh. Delivers value by eliminating timeout issues.

**Acceptance Scenarios**:

1. **Given** a workflow is marked as async, **When** a user triggers it from a form, **Then** the UI immediately returns with a "Queued" status
2. **Given** an async workflow is running, **When** the user is on the history page, **Then** the status updates automatically every 5-10 seconds without page refresh
3. **Given** an async workflow completes, **When** the user views the execution log, **Then** the result is available with completion timestamp
4. **Given** a workflow has an option to return immediate results, **When** it's triggered asynchronously, **Then** partial results are available immediately while full results come later
5. **Given** multiple async workflows are queued, **When** a worker picks them up, **Then** they execute in order with proper context and permissions
6. **Given** a sync workflow is still desired, **When** a user triggers a workflow, **Then** they can choose sync or async execution mode

---

### User Story 5 - CRON-Scheduled Workflows (Priority: P2)

Platform administrators need to schedule workflows to run automatically on a recurring basis using CRON expressions, with visibility into the schedule in the UI.

**Why this priority**: Scheduled workflows enable automated maintenance, report generation, and periodic data sync. Important for automation but not blocking for manual workflows.

**Independent Test**: Can be fully tested by creating a workflow with a CRON schedule, waiting for the trigger time, and verifying execution logs show automatic runs. Delivers value by enabling time-based automation.

**Acceptance Scenarios**:

1. **Given** a workflow has a CRON schedule configured, **When** viewing the workflow details, **Then** the schedule is displayed in human-readable format (e.g., "Every day at 2:00 AM")
2. **Given** a CRON schedule is set to run every 5 minutes, **When** the time arrives, **Then** the workflow executes automatically with global scope permissions
3. **Given** a scheduled workflow fails, **When** viewing execution history, **Then** the failure is logged with error details and timestamp
4. **Given** a CRON schedule is disabled, **When** the trigger time arrives, **Then** the workflow does not execute
5. **Given** multiple workflows have overlapping schedules, **When** trigger times arrive, **Then** all workflows execute without blocking each other

---

### User Story 6 - Enhanced Search and Filtering Across All Pages (Priority: P2)

Users need full-text search and filtering capabilities on all pages with tables and cards, with automatic reloading when changing scope or entering pages.

**Why this priority**: As data grows, finding specific workflows, executions, or configurations becomes time-consuming. Search improves usability but existing browsing still works.

**Independent Test**: Can be fully tested by entering a search term on the workflows page and verifying results filter immediately. Delivers value by improving navigation efficiency.

**Acceptance Scenarios**:

1. **Given** a user is on any page with tables or cards, **When** they enter text in the search box, **Then** results filter immediately without requiring a button click
2. **Given** a user enters a page with data, **When** the page loads, **Then** data is fetched automatically without requiring a manual refresh
3. **Given** a user switches global scope (org selection), **When** viewing scoped resources (workflows, forms), **Then** the page reloads data automatically for the new scope
4. **Given** a user switches scope on an unscoped resource page (users), **When** the scope changes, **Then** the page does not reload (data is global)
5. **Given** the execution history has thousands of entries, **When** the user scrolls to the bottom, **Then** the next page of results loads automatically (pagination)

---

### User Story 7 - Platform Branding Customization (Priority: P3)

Platform administrators need to upload custom logos (square and rectangle) and change the primary color scheme to match their brand identity.

**Why this priority**: Branding is important for white-labeling and professional appearance but doesn't affect functionality. Nice-to-have for production deployments.

**Independent Test**: Can be fully tested by uploading a logo and changing the primary color, then verifying the changes appear in the sidebar and forms. Delivers value by enabling brand customization.

**Acceptance Scenarios**:

1. **Given** a platform admin is in the Branding settings, **When** they upload a square logo (PNG/SVG/JPG), **Then** the logo replaces the default logo in the sidebar
2. **Given** a platform admin uploads a rectangle logo, **When** users view a public form, **Then** the rectangle logo appears above the form title
3. **Given** a platform admin selects a primary color, **When** they save the settings, **Then** UI elements (buttons, links, highlights) use the new color throughout the platform
4. **Given** no custom branding is set, **When** users view the platform, **Then** default logos and colors are used
5. **Given** a platform admin uploads a 10MB logo file, **When** they attempt to save, **Then** the system rejects it with a file size limit error

---

### User Story 8 - Execution Logs with Advanced Indexing and Search (Priority: P3)

Users need to efficiently search execution history by user, workflow, status, and date range even with millions of execution logs.

**Why this priority**: Execution logs grow rapidly in production. Efficient search prevents performance degradation but current pagination works for smaller datasets.

**Independent Test**: Can be fully tested by creating 10,000 execution logs, then searching by workflow name and status within a date range. Delivers value by enabling efficient log analysis.

**Acceptance Scenarios**:

1. **Given** execution history has 1 million entries, **When** a user filters by workflow name, **Then** results return in under 2 seconds
2. **Given** a user searches by date range (last 7 days), **When** the filter is applied, **Then** only logs within that range are displayed
3. **Given** a user filters by status (Failed), **When** viewing results, **Then** only failed executions are shown with error details
4. **Given** a user combines multiple filters (workflow + status + date range), **When** all filters are active, **Then** results match all criteria
5. **Given** a user selects a specific execution log, **When** viewing details, **Then** input parameters, output results, and error traces are displayed

---

### User Story 9 - System Workspace with Built-in Workflows (Priority: P3)

Platform administrators need access to a system workspace folder containing example and test workflows that can be toggled as visible/hidden in the UI.

**Why this priority**: Example workflows help users learn the platform and built-in utilities reduce code duplication. Helpful for onboarding but not critical for operation.

**Independent Test**: Can be fully tested by viewing the system workspace folder, executing a system workflow, and verifying it runs correctly. Delivers value by providing ready-to-use examples.

**Acceptance Scenarios**:

1. **Given** the platform is deployed, **When** a platform admin views the workflows list, **Then** system workflows are hidden by default
2. **Given** a platform admin toggles "Show System Workflows", **When** viewing the workflows list, **Then** system workflows appear with a "System" badge
3. **Given** a user executes a system workflow, **When** the workflow runs, **Then** it has access to the system workspace folder
4. **Given** a developer creates a new system workflow, **When** the platform restarts, **Then** the workflow is automatically imported and available
5. **Given** a workflow imports `from bifrost import utils`, **When** the workflow executes, **Then** shared utilities are available
6. **Given** a workflow imports `from bifrost import openapi2python`, **When** the workflow executes, **Then** the custom library is available

---

### User Story 10 - Enhanced Authentication with Entra ID User Matching (Priority: P2)

The system needs to store and match users by Entra ID user ID first, then fall back to email, preventing duplicate accounts when usernames change.

**Why this priority**: Username changes breaking user accounts is a critical issue in production. This prevents data loss and access issues but requires careful migration.

**Independent Test**: Can be fully tested by changing a user's email in Entra ID, then logging in and verifying the same account is accessed. Delivers value by preventing account duplication.

**Acceptance Scenarios**:

1. **Given** a new user logs in via Entra ID, **When** their account is created, **Then** the Entra ID user ID is stored in their user record
2. **Given** an existing user without an Entra ID user ID logs in, **When** they authenticate, **Then** their record is updated with the Entra ID user ID
3. **Given** a user changes their email in Entra ID, **When** they log in, **Then** they are matched by Entra ID user ID (not email) and access their existing account
4. **Given** a user is matched by Entra ID user ID, **When** their email has changed, **Then** the system updates the email in the user record
5. **Given** a user cannot be matched by Entra ID user ID, **When** they log in, **Then** the system falls back to email matching

---

### Edge Cases

- What happens when a workflow running on form launch fails or times out?
- How does the system handle file uploads when storage quota is exceeded?
- What happens when a user references a non-existent field in a JavaScript visibility condition?
- How does the system handle concurrent workflow key regeneration requests?
- What happens when a CRON schedule overlaps with itself (workflow still running when next trigger arrives)?
- How does the system handle HTML component content that includes malicious scripts?
- What happens when a user changes scope while an async workflow is still running in the previous scope?
- How does the system handle Entra ID user ID collisions (same ID, different email)?
- What happens when a workflow key is used for a workflow that has been deleted?
- How does the system handle form submissions with file uploads that exceed maximum file size?

## Requirements *(mandatory)*

### Functional Requirements

#### Forms Enhancement

- **FR-001**: System MUST create a `context` object available throughout the form lifecycle containing workflow results, query parameters, and field values
- **FR-002**: Form creators MUST be able to select a workflow that executes automatically when the form launches
- **FR-003**: System MUST display a loading state while the launch workflow is running
- **FR-004**: System MUST make workflow results available in `context.workflow_result` after workflow completion
- **FR-005**: System MUST make query parameters available in `context.params` object (e.g., `/execute/{form_id}?foo=bar` → `context.params.foo`)
- **FR-006**: System MUST store field values in `context.field.{field_name}` as users make selections
- **FR-007**: Form creators MUST be able to set field visibility using JavaScript expressions evaluated against the context object
- **FR-008**: System MUST re-evaluate field visibility conditions whenever any field value changes
- **FR-009**: System MUST eliminate redundant global vs organization selection by automatically handling scope through existing scope switching mechanism
- **FR-010**: Form creators MUST be able to add static dropdown components with custom options visible to end users
- **FR-011**: System MUST provide a Text/Markdown component for displaying non-input information
- **FR-012**: System MUST provide an HTML component that accepts the entire context object for variable interpolation (e.g., `${context.field.first_name}`)
- **FR-013**: System MUST provide a Date/Time picker component
- **FR-014**: System MUST provide a Radio Button component
- **FR-015**: System MUST provide a File Upload component with configurable allowed file types
- **FR-016**: File Upload component MUST support multi-select dropdown for common file types and allow custom type entry
- **FR-017**: File Upload component MUST support multiple file uploads when enabled
- **FR-018**: File Upload component MUST always return files as a list, even for single file uploads
- **FR-019**: System MUST generate secure storage URIs for uploaded files and pass them to workflows

#### Workflow HTTP API

- **FR-020**: Platform administrators MUST be able to generate a global workflow API key that works for all workflows
- **FR-021**: Workflow owners MUST be able to generate per-workflow API keys that only work for specific workflows
- **FR-022**: System MUST validate HTTP requests using either global or workflow-specific keys in the `x-workflows-key` header
- **FR-023**: Workflows triggered via valid API keys MUST execute with global scope permissions (equivalent to Platform Admin)
- **FR-024**: Users MUST be able to regenerate both global and workflow-specific API keys
- **FR-025**: System MUST immediately invalidate old keys when regenerated
- **FR-026**: Workflow owners MUST be able to toggle HTTP access on/off per workflow
- **FR-027**: System MUST reject HTTP requests for workflows with HTTP access disabled
- **FR-028**: System MUST allow anonymous POST and GET requests to workflow endpoints when authenticated with valid keys
- **FR-029**: System MUST use a decorator (e.g., `@has_workflow_key`) to protect workflow endpoints
- **FR-030**: System MUST ensure all other endpoints remain properly secured since static web app config no longer provides blanket protection

#### Async Workflows

- **FR-031**: Workflow creators MUST be able to mark workflows as asynchronous
- **FR-032**: Async workflows MUST return immediately to the UI with a "Queued" status
- **FR-033**: System MUST provide a worker function that picks up queued workflows and executes them
- **FR-034**: Worker MUST preserve all context, parameters, and permissions when executing queued workflows
- **FR-035**: Workflow creators MUST be able to configure whether async workflows return immediate partial results
- **FR-036**: Users MUST be able to choose sync vs async execution mode when triggering workflows directly
- **FR-037**: Form creators MUST be able to specify sync or async execution when binding workflows to forms
- **FR-038**: System MUST avoid duplicating workflow execution logic between sync and async paths
- **FR-039**: UI MUST display "Queued", "Running", "Completed", or "Failed" status for async workflows
- **FR-040**: System MUST refresh execution status for unfinished workflows every 5-10 seconds while user is viewing the history page
- **FR-041**: System MUST use React memoization to prevent UI flashing during status refreshes

#### CRON Scheduled Workflows

- **FR-042**: Workflow creators MUST be able to configure CRON schedules for automatic execution
- **FR-043**: System MUST display CRON schedules in human-readable format in the UI (e.g., "Every day at 2:00 AM")
- **FR-044**: System MUST execute scheduled workflows automatically at specified times
- **FR-045**: Scheduled workflows MUST run with global scope permissions
- **FR-046**: System MUST log all scheduled executions in execution history with trigger type
- **FR-047**: System MUST handle overlapping schedules (workflow still running when next trigger arrives) by queuing or skipping based on configuration

#### Search and Filtering

- **FR-048**: All pages with tables or cards MUST include a full-text search box
- **FR-049**: System MUST filter results immediately as users type in the search box
- **FR-050**: System MUST automatically load data when users enter pages with tables or cards
- **FR-051**: System MUST automatically reload scoped resources when users switch global scope (organization selection)
- **FR-052**: System MUST NOT reload unscoped resources (e.g., users, global configs) when scope changes
- **FR-053**: Execution history MUST support pagination to handle millions of log entries
- **FR-054**: System MUST support filtering execution history by user, workflow, status, and date range
- **FR-055**: System MUST use efficient indexing to enable fast searches even with large datasets

#### Platform Branding

- **FR-056**: Platform administrators MUST be able to upload custom square logos (PNG, JPG, SVG) for the sidebar
- **FR-057**: Platform administrators MUST be able to upload custom rectangle logos for form headers
- **FR-058**: System MUST support all common image formats including SVG
- **FR-059**: Platform administrators MUST be able to change the primary color theme
- **FR-060**: System MUST replace sidebar logo with custom square logo when configured
- **FR-061**: System MUST display rectangle logo above form titles when configured
- **FR-062**: System MUST apply custom primary color to UI elements throughout the platform
- **FR-063**: System MUST store branding settings in a Settings section under a Branding tab
- **FR-064**: System MUST use default logos and colors when custom branding is not configured

#### Execution Logs

- **FR-065**: System MUST create indexes on execution logs for efficient searching by user, workflow, status, and date range
- **FR-066**: System MUST structure RowKeys to enable efficient date range queries
- **FR-067**: System MUST return execution log search results in under 2 seconds for datasets with 1+ million entries
- **FR-068**: Users MUST be able to view full execution details including input, output, and error traces

#### System Workspace

- **FR-069**: System MUST maintain a system workspace folder available to all workflows
- **FR-070**: System MUST auto-import workflows from the system workspace folder on platform startup
- **FR-071**: System workflows MUST be labeled as "System" in the UI
- **FR-072**: System workflows MUST be hidden by default in the UI
- **FR-073**: Platform administrators MUST be able to toggle system workflows as visible
- **FR-074**: System MUST provide a shared utilities module importable as `from bifrost import utils`
- **FR-075**: System MUST support custom library modules in the utilities folder (e.g., `from bifrost import openapi2python`)

#### Enhanced Authentication

- **FR-076**: System MUST store Entra ID user ID when creating new user accounts via authorization
- **FR-077**: System MUST update existing user records with Entra ID user ID during login if not already set
- **FR-078**: System MUST first attempt to match users by Entra ID user ID during authentication
- **FR-079**: System MUST fall back to email matching if no Entra ID user ID match is found
- **FR-080**: System MUST update user email addresses when matched by Entra ID user ID but email has changed
- **FR-081**: System MUST prevent duplicate account creation when usernames change in Entra ID

### Key Entities

- **Form Context**: Runtime object containing workflow results, query parameters, and field values available throughout the form lifecycle. Attributes include workflow_result (object), params (key-value map), field (key-value map of field names to values).

- **Workflow API Key**: Authentication credential for HTTP workflow access. Attributes include key value (encrypted), scope (global or workflow-specific), workflow_id (for workflow-specific keys), created_at, created_by, last_used_at.

- **Async Workflow Execution**: Queued workflow job awaiting worker pickup. Attributes include queue_id, workflow_id, parameters, context, scope, status (queued/running/completed/failed), queued_at, started_at, completed_at, result.

- **CRON Schedule**: Recurring schedule for automatic workflow execution. Attributes include workflow_id, cron_expression, enabled (boolean), last_run_at, next_run_at.

- **Platform Branding**: Organization-level or global branding configuration. Attributes include square_logo_url, rectangle_logo_url, primary_color, organization_id (null for global).

- **System Workflow**: Built-in workflow stored in system workspace. Attributes include workflow_id, name, system_flag (boolean), visible (boolean), workspace_path.

- **Entra ID User Mapping**: Link between platform user and Entra ID identity. Attributes include user_id, entra_user_id, email, last_updated.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Form creators can build a form with a launch workflow, dynamic visibility, and file uploads in under 10 minutes
- **SC-002**: Forms with context-based visibility respond to field changes in under 100ms (instant feedback)
- **SC-003**: 95% of workflow HTTP API calls authenticate successfully within 200ms
- **SC-004**: Async workflows return "Queued" status to users in under 500ms regardless of workflow complexity
- **SC-005**: Execution history searches return results in under 2 seconds even with 1 million+ log entries
- **SC-006**: Users can find specific workflows using search in under 5 seconds on pages with 1000+ workflows
- **SC-007**: Platform administrators can upload custom branding and see changes reflected in under 30 seconds
- **SC-008**: CRON-scheduled workflows execute within 10 seconds of their scheduled time 99% of the time
- **SC-009**: Duplicate accounts due to Entra ID email changes are reduced to zero
- **SC-010**: Users can upload files up to 100MB through forms without timeout failures
- **SC-011**: 90% of users successfully create dynamic forms with conditional fields on first attempt
- **SC-012**: System handles 100 concurrent workflow HTTP API requests without degradation
- **SC-013**: Form loading with launch workflows completes in under 3 seconds for 90% of workflows
- **SC-014**: Execution history auto-refresh updates status without noticeable UI flicker or performance impact
- **SC-015**: Platform supports 10,000+ workflows with full search and filtering capabilities maintained
