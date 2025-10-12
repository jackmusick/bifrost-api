# Feature Specification: Bifrost Integrations MVP

**Feature Branch**: `001-complete-mvp-for`
**Created**: 2025-10-10
**Status**: Draft
**Input**: Complete MVP for Bifrost Integrations - a code-first Rewst alternative with tenant management, GDAP integration, form builder with data providers, workflow engine with Python decorators, and multi-tenant permissions

## User Scenarios & Testing

### User Story 1 - Organization Management (Priority: P1)

An MSP administrator needs to manage client organizations and link them to Microsoft 365 tenants via GDAP (Granular Delegated Admin Privileges) to enable automated workflows.

**Why this priority**: Organizations are the foundation of the multi-tenant platform. Without organizations, no other features can function since everything is org-scoped.

**Independent Test**: Can be fully tested by creating an organization, linking it to a test GDAP tenant, storing configuration values, and verifying data isolation between organizations.

**Acceptance Scenarios**:

1. **Given** I am logged in as an MSP admin, **When** I navigate to the organizations page, **Then** I see a list of all client organizations with their names and GDAP tenant status
2. **Given** I am creating a new organization, **When** I provide an organization name and optional GDAP tenant ID, **Then** the organization is created and I can store configuration key-value pairs for that organization
3. **Given** I have an organization linked to a GDAP tenant, **When** workflows execute for that organization, **Then** they automatically receive the correct tenant context and credentials
4. **Given** I am viewing an organization's configuration, **When** I add or update configuration values, **Then** workflows can access these values via the organization context
5. **Given** I have multiple organizations, **When** I query data for organization A, **Then** I only see data for organization A and never data from organization B

---

### User Story 2 - User Authentication & Permissions (Priority: P1)

MSP technicians need to log in with their Microsoft 365 accounts and have granular permissions to access specific client organizations and perform specific actions.

**Why this priority**: Security and multi-tenancy are non-negotiable. Users must only access organizations they're authorized for.

**Independent Test**: Can be tested by creating users with different permission sets, attempting to access various organizations, and verifying permission enforcement at the API level.

**Acceptance Scenarios**:

1. **Given** I am an MSP technician, **When** I visit the platform, **Then** I am redirected to Microsoft Azure AD login
2. **Given** I have successfully authenticated, **When** I access the platform, **Then** I only see organizations I have been granted access to
3. **Given** I am an admin granting permissions, **When** I assign a user access to an organization, **Then** I can specify granular permissions (execute workflows, manage config, manage forms, view history)
4. **Given** I only have permission to execute workflows for organization A, **When** I attempt to manage forms for organization A, **Then** I receive an authorization error
5. **Given** I have no permissions for organization B, **When** I attempt any action on organization B, **Then** all API requests are denied

---

### User Story 3 - Workflow Development & Registration (Priority: P1)

A developer needs to write Python workflows using decorators that automatically register with the platform and expose metadata for form generation.

**Why this priority**: The workflow engine is the core value proposition. Without it, there's no automation. This enables the "code-first" experience.

**Independent Test**: Can be tested by creating a simple Python workflow with the `@workflow` decorator, starting the workflow engine, and verifying the workflow appears in the metadata endpoint with correct parameter definitions.

**Acceptance Scenarios**:

1. **Given** I am developing a new automation, **When** I create a Python function with the `@workflow` decorator and parameter annotations, **Then** the workflow is automatically discovered and registered when the workflow engine starts
2. **Given** I have defined workflow parameters with types and validation rules, **When** the Management UI fetches workflow metadata, **Then** it receives complete information about parameters, types, required fields, and linked data providers
3. **Given** I am debugging a workflow locally, **When** I run the Python function directly with mock context, **Then** I can set breakpoints and step through the code with my IDE's debugger
4. **Given** I have created a workflow, **When** I deploy the workflow engine, **Then** the workflow is immediately available for execution without any manual registration steps
5. **Given** I want to test a workflow without organization context, **When** I use `@workflow(requires_org=False)`, **Then** I can execute the workflow with just input parameters and no org context

---

### User Story 4 - Data Providers for Dynamic Form Fields (Priority: P2)

Developers need to create data provider functions that supply dynamic options for form fields, similar to Rewst's option generators but with a more semantic name.

**Why this priority**: Forms need dynamic data (e.g., "available licenses for this tenant"). This is required for real-world workflows but can be added after basic workflow execution works.

**Independent Test**: Can be tested by creating a data provider that returns a list of items, creating a form field that references it, and verifying the form receives the correct options when rendered.

**Acceptance Scenarios**:

1. **Given** I am developing a workflow that needs a dropdown of available Microsoft 365 licenses, **When** I create a function with the `@data_provider` decorator, **Then** forms can reference this provider to populate dropdown options
2. **Given** I have defined a data provider, **When** a form field is configured to use that provider, **Then** the UI calls the provider endpoint with organization context and receives a list of label-value pairs
3. **Given** a data provider requires organization-specific data, **When** it executes, **Then** it automatically receives organization context including config, secrets, and integration clients
4. **Given** I want to provide options based on user input, **When** I define parameters on my data provider, **Then** the UI can pass those parameters when calling the provider
5. **Given** a data provider fails or returns an error, **When** a form attempts to load options, **Then** the user sees a helpful error message and the form remains functional

---

### User Story 5 - Form Builder (Priority: P2)

An MSP administrator needs to create forms with various field types that are linked to workflows and use data providers for dynamic fields.

**Why this priority**: Forms are the primary user interface for workflow execution. Required for non-technical users to run workflows.

**Independent Test**: Can be tested by creating a form with multiple field types (text, email, select, checkbox), linking it to a workflow, and verifying the form can be saved and retrieved.

**Acceptance Scenarios**:

1. **Given** I am creating a new form, **When** I specify a form name, description, and linked workflow, **Then** the form is created and associated with that workflow
2. **Given** I am adding fields to a form, **When** I add fields of various types (text, email, number, select, checkbox, textarea), **Then** each field is saved with its type, label, validation rules, and required status
3. **Given** I am configuring a select field, **When** I choose to use a data provider, **Then** I can select from available data providers registered in the workflow engine
4. **Given** I have created a form, **When** I save it, **Then** it is stored with the organization it belongs to (or marked as GLOBAL for shared forms)
5. **Given** I am viewing my forms list, **When** I load the page, **Then** I see forms I've created for my organizations plus any GLOBAL forms available to all organizations

---

### User Story 6 - Form Renderer & Submission (Priority: P2)

An MSP technician needs to view and submit forms to execute workflows, with dynamic field options loaded from data providers.

**Why this priority**: This completes the user-facing workflow execution flow. Without it, only developers can execute workflows via API calls.

**Independent Test**: Can be tested by rendering a form, filling in fields (including a select field with dynamic options), submitting it, and verifying the workflow is executed with the correct parameters.

**Acceptance Scenarios**:

1. **Given** I select a form to execute, **When** the form loads, **Then** I see all fields rendered according to their types with labels and validation rules
2. **Given** a form has a select field with a data provider, **When** the form loads, **Then** the data provider is called for my current organization and the dropdown is populated with the returned options
3. **Given** I am filling out a form, **When** I provide invalid data (wrong format, missing required field), **Then** I see inline validation errors before I can submit
4. **Given** I have completed a form, **When** I submit it, **Then** the linked workflow is executed with my form data and I see a confirmation with execution ID
5. **Given** a workflow is executing, **When** I wait for completion, **Then** I see the execution result (success or failure) with any output data or error messages

---

### User Story 7 - Workflow Execution with Organization Context (Priority: P1)

Workflows need to automatically receive organization context including config, secrets, and pre-authenticated integration clients when executed.

**Why this priority**: This is the core automation capability. Workflows must access org-specific data and integrations to be useful.

**Independent Test**: Can be tested by executing a workflow that accesses organization config, retrieves a secret, and uses an integration client, verifying all context is correctly loaded.

**Acceptance Scenarios**:

1. **Given** I have submitted a form to execute a workflow, **When** the workflow executes, **Then** it automatically receives an organization context object without any manual loading
2. **Given** a workflow needs organization-specific configuration, **When** it accesses `context.config.get('setting_name')`, **Then** it receives the value stored in Table Storage for that organization
3. **Given** a workflow needs to access a secret, **When** it calls `await context.secrets.get('secret_name')`, **Then** it receives the secret from Azure Key Vault scoped to that organization
4. **Given** a workflow needs to call Microsoft Graph API, **When** it calls `context.get_integration('msgraph')`, **Then** it receives a pre-authenticated client for that organization's tenant
5. **Given** a workflow completes execution, **When** it returns results, **Then** the execution is logged to Table Storage with status, input, output, duration, and caller information

---

### User Story 8 - Execution History & Audit Trail (Priority: P3)

MSP technicians need to view a history of workflow executions to monitor automation activity, troubleshoot issues, and maintain an audit trail.

**Why this priority**: Important for operations and troubleshooting but not blocking for initial development. Can be added after core execution works.

**Independent Test**: Can be tested by executing several workflows, then querying execution history and verifying all executions are recorded with correct timestamps, status, and details.

**Acceptance Scenarios**:

1. **Given** I am viewing execution history, **When** I select an organization, **Then** I see a list of recent workflow executions for that organization with status, workflow name, executed by, and timestamp
2. **Given** I am viewing a specific execution, **When** I open the execution details, **Then** I see the complete input parameters, output results, execution duration, and any error messages
3. **Given** I want to troubleshoot a failure, **When** I filter executions by status "Failed", **Then** I see only failed executions with error details readily available
4. **Given** I want to see my own execution history, **When** I filter by "My Executions", **Then** I see all workflows I have personally executed across all my authorized organizations
5. **Given** an execution has been logged, **When** I view it, **Then** I see complete audit information including who executed it, when, from what IP address, and what the result was

---

### User Story 9 - User Management & Roles (Priority: P2)

MSP administrators need to view all platform users (MSP technicians and organization users), assign roles for form access control, and users need to view their own profile.

**Why this priority**: Essential for administering platform access and controlling which organization users can execute which forms, but not blocking for initial MSP technician workflows.

**Independent Test**: Can be tested by auto-creating users on first login, assigning roles to organization users, and verifying role-based form access.

**Architecture Note**: Users are auto-created via Entra ID (Azure AD) SSO. No password/email management needed. Two user types exist: MSP (technicians with full access) and ORG (organization users with role-based form access).

**Acceptance Scenarios**:

1. **Given** a new user logs in for the first time via Entra ID, **When** they authenticate, **Then** their user record is automatically created with email, display name, and last login timestamp
2. **Given** I am an MSP administrator viewing the users page, **When** I see the user list, **Then** I can filter by user type (MSP technicians vs organization users) and see last login time for each
3. **Given** I want to control form access, **When** I create a role (e.g., "Billing Admins"), **Then** I can assign organization users to that role and grant the role access to specific forms
4. **Given** an organization user has been assigned roles, **When** they log in, **Then** they only see forms that their roles have been granted access to
5. **Given** I need to remove access, **When** I soft-delete a user (set IsActive=false), **Then** they can no longer log in but their execution history is preserved for audit purposes

---

### User Story 10 - Global Configuration & Secret Management (Priority: P2)

MSP administrators need to manage global MSP-level configuration and secrets (with optional organization-specific overrides) to enable workflows to access integrations and environment variables.

**Why this priority**: Required for workflows to access MSP credentials and configuration but can be added after basic workflow execution works.

**Independent Test**: Can be tested by setting global config/secrets, adding org-specific overrides, and verifying workflow context loads with correct fallback behavior (org → global).

**Architecture Note**:

-   **Config**: Combined table with `PartitionKey="GLOBAL"` for MSP-wide settings or `PartitionKey={orgId}` for overrides. Lookup order: org → global → none.
-   **Secrets**: Key Vault with `GLOBAL--secret-name` for MSP credentials or `{orgId}--secret-name` for org overrides. Lookup order: org → global → none.
-   **Integration code**: Developers write integration clients (`msgraph.py`, `halopsa.py`) in workflows repo. UI only manages config/secrets, not code.

**Acceptance Scenarios**:

1. **Given** I am setting up the MSP platform, **When** I configure global settings, **Then** I can add MSP-wide config (e.g., `halo_api_url`) and secrets (e.g., `GLOBAL--msgraph-secret`) that all workflows can access by default
2. **Given** a specific organization needs different credentials, **When** I add an org-specific secret override (e.g., `{orgId}--msgraph-secret`), **Then** workflows for that organization use the override instead of the global secret
3. **Given** I am managing configuration, **When** I view the config page, **Then** I can see global configs separately from org-specific overrides with clear indication of which org overrides which global values
4. **Given** a workflow needs a config value, **When** it calls `context.config.get('halo_api_url')`, **Then** it receives the org-specific value if set, otherwise falls back to the global value
5. **Given** a workflow needs a secret, **When** it calls `await context.secrets.get('msgraph_secret')`, **Then** the system checks `{orgId}--msgraph_secret` first, falls back to `GLOBAL--msgraph_secret`, and returns None if neither exists

---

### User Story 11 - Workflow Catalog & Metadata-Driven Forms (Priority: P2)

MSP technicians need to browse available workflows, view their metadata (parameters, types, data providers), and automatically generate forms from workflow parameter definitions.

**Why this priority**: Enables non-developers to create forms and improves workflow discoverability. Not blocking but significantly improves UX.

**Independent Test**: Can be tested by viewing a workflow with `@param` decorators, seeing the parameter metadata, and auto-generating a form that maps parameters to form fields.

**Architecture Note**: Workflows expose metadata via `@param` decorators (e.g., `@param("license", type="select", options_from="get_available_licenses")`). The UI can auto-generate forms from this metadata or allow manual form creation.

**Acceptance Scenarios**:

1. **Given** I am browsing workflows, **When** I navigate to the workflows page, **Then** I see a searchable catalog of all registered workflows with their names, descriptions, and categories
2. **Given** I am viewing a workflow, **When** I click on a workflow in the catalog, **Then** I see its parameter metadata including name, type, required status, and linked data providers
3. **Given** I want to create a form for a workflow, **When** I click "Auto-Generate Form" on a workflow's detail page, **Then** the system creates a form with fields matching each `@param` decorator definition
4. **Given** a workflow parameter uses `options_from="data_provider_name"`, **When** I auto-generate a form, **Then** the corresponding form field is created as a select dropdown linked to that data provider
5. **Given** I want to execute a workflow with simple parameters, **When** I view workflow details, **Then** I can execute it directly with an inline form without creating a saved form

---

### User Story 12 - System Monitoring & Health (Priority: P3)

MSP administrators need to monitor the health of Azure Functions, view system status, and receive alerts when services are degraded.

**Why this priority**: Important for operations but not blocking for MVP. Can rely on Azure portal monitoring initially.

**Independent Test**: Can be tested by checking Azure Functions status, viewing recent errors, and displaying system health indicators.

**Acceptance Scenarios**:

1. **Given** I am viewing the system dashboard, **When** I access the admin panel, **Then** I see health status for Management API and Workflow Engine (running, degraded, down)
2. **Given** I want to monitor performance, **When** I view system metrics, **Then** I see API response times, workflow execution counts, and error rates for the past 24 hours
3. **Given** there are recent system errors, **When** I check the system health page, **Then** I see recent exceptions, failed requests, and their error messages
4. **Given** I want to verify Azure resources, **When** I check resource status, **Then** I see Table Storage connectivity, Key Vault accessibility, and Function App deployment status
5. **Given** a critical service is down, **When** I access the platform, **Then** I see a prominent banner alerting me to the issue with an estimate of impact

---

### Edge Cases

-   What happens when a GDAP tenant ID is invalid or the MSP no longer has access to the tenant?
-   How does the system handle a data provider that times out or returns malformed data?
-   What happens when a workflow fails with an exception - how is this communicated to the user?
-   How does the system handle concurrent form submissions for the same workflow?
-   What happens when a user's permissions are revoked while they have an active session?
-   How does the system handle workflows that take longer than standard HTTP timeout periods?
-   What happens when organization configuration values are missing but a workflow expects them?
-   How does the system handle secrets that don't exist in Key Vault?
-   What happens when Table Storage is temporarily unavailable?
-   How are workflow parameter validation errors distinguished from execution errors?

## Requirements

### Functional Requirements

-   **FR-001**: System MUST allow MSP administrators to create, read, update, and delete client organizations
-   **FR-002**: System MUST allow organizations to be linked to Microsoft 365 GDAP tenant IDs
-   **FR-003**: System MUST store organization-specific configuration as key-value pairs isolated by organization
-   **FR-004**: System MUST authenticate users via Azure Active Directory single sign-on
-   **FR-005**: System MUST enforce org-scoped permissions for all data access (no cross-org data leakage)
-   **FR-006**: System MUST support granular permissions per user per organization (execute workflows, manage config, manage forms, view history)
-   **FR-007**: System MUST allow developers to define workflows using Python decorator syntax (`@workflow`)
-   **FR-008**: System MUST automatically discover and register decorated workflows at startup
-   **FR-009**: System MUST provide a metadata endpoint that exposes workflow definitions with parameter details
-   **FR-010**: System MUST support workflow parameter types (string, number, email, boolean, select) with validation
-   **FR-011**: System MUST allow developers to create data provider functions using `@data_provider` decorator
-   **FR-012**: System MUST expose data provider endpoints that return label-value pairs for form fields
-   **FR-013**: System MUST allow administrators to create forms with configurable fields (text, email, number, select, checkbox, textarea)
-   **FR-014**: System MUST link forms to specific workflows for execution
-   **FR-015**: System MUST allow form fields to reference data providers for dynamic options
-   **FR-016**: System MUST render forms with client-side validation based on field types and rules
-   **FR-017**: System MUST execute workflows when forms are submitted with form data as parameters
-   **FR-018**: System MUST automatically load organization context when workflows execute
-   **FR-019**: System MUST provide workflows access to organization config, secrets, and integration clients via context object
-   **FR-020**: System MUST pre-authenticate integration clients (Microsoft Graph, HaloPSA) using organization credentials
-   **FR-021**: System MUST log all workflow executions with input, output, status, duration, and caller information
-   **FR-022**: System MUST store execution history with dual-indexing for org-scoped and user-scoped queries
-   **FR-023**: System MUST display execution history filtered by organization, user, status, or date range
-   **FR-024**: System MUST allow developers to debug workflows locally with standard Python debugging tools
-   **FR-025**: System MUST support workflows that don't require organization context (`requires_org=False`)
-   **FR-026**: System MUST provide a user management interface showing all platform users with their access levels
-   **FR-027**: System MUST auto-create user records when users first authenticate via Azure AD
-   **FR-028**: System MUST allow users to view their own profile including organizations they can access
-   **FR-029**: System MUST provide integration configuration UI for setting up Microsoft Graph, HaloPSA, and other external services per organization
-   **FR-030**: System MUST securely store integration credentials and secrets in Azure Key Vault with org-scoped access
-   **FR-031**: System MUST display workflow catalog with search and filtering capabilities
-   **FR-032**: System MUST show workflow details including parameters, types, descriptions, and linked data providers
-   **FR-033**: System MUST provide system health dashboard showing API and workflow engine status
-   **FR-034**: System MUST track and display system metrics including response times, execution counts, and error rates

### Key Entities

-   **Organization**: Represents a client company with optional GDAP tenant link, configuration, and permissions
-   **User**: MSP technician authenticated via Azure AD with org-scoped permissions
-   **UserPermission**: Many-to-many relationship between users and organizations with granular permission flags
-   **Workflow**: Python function registered via decorator with metadata about parameters and execution requirements
-   **DataProvider**: Python function that provides dynamic data for form fields
-   **Form**: User-facing interface with fields linked to a workflow
-   **FormField**: Individual input field with type, validation, and optional data provider reference
-   **WorkflowExecution**: Record of a workflow run with input, output, status, and audit information
-   **OrganizationConfig**: Key-value configuration storage scoped to an organization
-   **IntegrationConfig**: Settings for external service integrations (Microsoft Graph, HaloPSA) per organization

## Success Criteria

### Measurable Outcomes

-   **SC-001**: MSP technicians can create a new organization and link it to a GDAP tenant in under 2 minutes
-   **SC-002**: Developers can create a new Python workflow and see it available in the UI within 30 seconds of deployment
-   **SC-003**: Form submissions execute workflows and return results in under 5 seconds for typical operations
-   **SC-004**: The platform supports 50 concurrent workflow executions without performance degradation
-   **SC-005**: Developers can set breakpoints in workflow code and debug locally using VSCode or PyCharm
-   **SC-006**: Organization context loading (config, integrations) completes in under 20 milliseconds
-   **SC-007**: 100% of API requests enforce org-scoped permissions with no cross-org data leakage in security testing
-   **SC-008**: Data providers return dynamic options for form fields in under 2 seconds for typical queries
-   **SC-009**: Users can navigate to a form, fill it out, and execute a workflow in under 90 seconds
-   **SC-010**: Execution history queries for a single organization return results in under 200 milliseconds
-   **SC-011**: The platform handles 50-200 organizations with 10-100 forms per organization without performance issues
-   **SC-012**: Developers can add a new integration client and have it available to workflows in under 1 hour of development time
-   **SC-013**: Failed workflow executions provide clear error messages that enable troubleshooting without code inspection
-   **SC-014**: The platform operates with zero cross-organization data leaks during penetration testing
-   **SC-015**: All workflow executions are logged with complete audit trails for compliance requirements

## User Interface & Experience Requirements

### UI Quality Standards

-   **UI-001**: Users MUST be able to navigate between all major sections (organizations, workflows, forms, execution history) in under 2 clicks from any page
-   **UI-002**: Forms MUST provide real-time validation feedback as users type, showing errors inline before submission
-   **UI-003**: The interface MUST be responsive and functional on desktop browsers (1920x1080 minimum, with support down to 1366x768)
-   **UI-004**: All interactive elements (buttons, form fields, dropdowns) MUST have clear visual feedback for hover, focus, and disabled states
-   **UI-005**: Loading states MUST be shown for any operation taking longer than 200ms (spinners, skeleton screens, or progress indicators)
-   **UI-006**: Error messages MUST be displayed in a consistent, user-friendly format with clear actionable guidance
-   **UI-007**: The interface MUST use consistent spacing, typography, and color schemes throughout all pages
-   **UI-008**: Form fields with data providers MUST show loading states while options are being fetched
-   **UI-009**: Complex forms MUST be broken into logical sections with clear visual hierarchy
-   **UI-010**: Users MUST be able to complete common workflows (create org, execute workflow, view history) without referring to documentation

### Component Architecture Requirements

-   **UI-011**: UI components MUST be small, focused, and reusable (single responsibility principle)
-   **UI-012**: Each component MUST handle only one concern (e.g., a button component should not contain business logic)
-   **UI-013**: Complex pages MUST be composed of multiple smaller components rather than monolithic page components
-   **UI-014**: Shared UI components (buttons, inputs, cards, tables) MUST be consistent across the entire application
-   **UI-015**: Components MUST accept props for customization rather than hard-coding values or styles

### State Management Requirements

-   **UI-016**: Application state MUST be managed efficiently to prevent unnecessary re-renders
-   **UI-017**: Global state (user authentication, selected organization) MUST be accessible across components without prop drilling
-   **UI-018**: Server state (API data) MUST be separated from client state (UI toggles, form input)
-   **UI-019**: Form state MUST be managed with proper validation and error handling
-   **UI-020**: State updates MUST be predictable and debuggable

### Code Quality Requirements

-   **UI-021**: All TypeScript code MUST compile without errors in strict mode
-   **UI-022**: All components MUST have proper TypeScript types for props and return values (no `any` types unless absolutely necessary)
-   **UI-023**: Code MUST pass linting checks before commit
-   **UI-024**: Component files MUST follow consistent naming conventions (PascalCase for components, camelCase for utilities)
-   **UI-025**: Complex logic MUST be extracted into custom hooks or utility functions for testability

### Visual Design Constraints

-   **UI-026**: The interface MUST use a professional, clean design suitable for enterprise MSP technicians
-   **UI-027**: Color palette MUST provide sufficient contrast for accessibility (WCAG AA minimum)
-   **UI-028**: Typography MUST be legible at standard screen distances with clear hierarchy (headings, body, captions)
-   **UI-029**: Interactive elements MUST be touch-friendly (minimum 44x44px tap targets) even though primary use is desktop
-   **UI-030**: The design system MUST be consistent - reusing the same patterns for similar actions throughout the app

## Assumptions

-   Azure AD tenant is already configured for the MSP organization
-   Developers have basic Python knowledge and familiarity with async/await patterns
-   Microsoft 365 GDAP relationships are established outside this platform
-   Azure resources (Table Storage, Key Vault, Functions) are provisioned via infrastructure-as-code
-   MSP has appropriate Microsoft CSP/GDAP permissions for client tenants
-   Network connectivity to Azure services is reliable and available
-   Local development uses Azurite for Table Storage emulation
-   Browser users have modern browsers supporting JavaScript ES6+
-   Organization configuration values use string serialization (JSON for complex types)
-   Workflow execution timeout is 5 minutes for standard operations (configurable per workflow)
-   Data provider results are limited to 1000 items maximum for performance
-   Forms are limited to 50 fields to ensure reasonable UI performance
-   Execution history is retained for 90 days by default
-   Secrets in Key Vault follow naming convention: `GLOBAL--{secret-name}` for MSP-wide or `{org-id}--{secret-name}` for org overrides
-   Integration authentication uses service principal credentials stored in Key Vault (global by default, org override if needed)
-   Configuration uses combined table: `PartitionKey="GLOBAL"` for MSP-wide or `PartitionKey={orgId}` for org overrides
-   Workflow context uses fallback pattern: check org-specific first, then global, then return None
-   Users are auto-created on first Entra ID login - no password/email management in platform
-   Two user types: MSP (technicians with full access) and ORG (organization users with role-based form access)
-   Form access for ORG users controlled via Roles system (MSP users bypass role checks)
