# Feature Specification: Azure Key Vault Integration for Secret Management

**Feature Branch**: `003-use-azure-key`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "Use Azure Key Vault for secret configs. This needs to work in local development and production. Ideally the config option for secrets ref would actually provide dropdown options through list permissions. Also, I understand we intended to have a get_config and get_secret. I'm not sure what the separation is for -- couldn't get_config decide where to get the value based on the config type?"

## Clarifications

### Session 2025-10-12

- Q: Should the platform provide secret management capabilities? → A: Limited write access - Platform allows creating/updating secrets but not deleting (deletion handled externally) **[UPDATED]** Full secret management - Platform provides create, update, and delete operations so users never need to access Key Vault directly
- Q: How should the platform determine which secure store instance to connect to in local development? → A: Environment variable configuration - Developers specify the secure store URL/name via environment variable or local settings file
- Q: Who should have permission to create and update secrets through the platform UI? → A: Platform admins only - Only users with platform-wide admin role can manage secrets
- Q: When displaying secrets in the UI (dropdown, list view, or after creation), how should secret values be handled? → A: Show on creation only - Display value immediately after creation, then mask thereafter
- Q: Should the platform provide any automated setup or validation for the secure store configuration? → A: Validation only - Platform validates secure store connectivity and permissions; ARM template handles provisioning and access policies

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Unified Configuration Access (Priority: P1)

As a workflow developer, I want to retrieve configuration values using a single unified method that automatically resolves secret references, so I don't need to know or care whether a value is stored as plain configuration or as a secure secret.

**Why this priority**: This is the core developer experience improvement. It eliminates confusion about when to use different methods for different value types and makes the system more intuitive. Without this, developers must understand the storage mechanism, which violates abstraction principles.

**Independent Test**: Can be fully tested by configuring a secret reference (e.g., `api_key` marked as secret type), then requesting that configuration value in a workflow and verifying the actual secret value is returned from the secure secret store.

**Acceptance Scenarios**:

1. **Given** a workflow needs an API key stored securely, **When** developer requests the `api_key` configuration, **Then** system returns the secret value transparently
2. **Given** a config value is stored as plain text, **When** developer requests the `timeout` configuration, **Then** system returns the value directly
3. **Given** a config value references a secret named `msgraph-client-secret`, **When** developer requests the `client_secret` configuration, **Then** system retrieves and returns the secret value
4. **Given** an org-specific secret doesn't exist, **When** system attempts to resolve the secret reference, **Then** it falls back to platform-wide secret before failing

---

### User Story 2 - Secret Configuration UI with Dropdown Selection (Priority: P2)

As a platform administrator, I want to select from existing secrets when configuring a secret reference config value in the UI, so I can avoid typos and see what secrets are available.

**Why this priority**: Enhances usability and reduces configuration errors. While administrators could manually type secret names, providing a dropdown prevents mistakes and improves discoverability. This is P2 because the system can function without it (manual entry works), but it significantly improves the admin experience.

**Independent Test**: Can be fully tested by opening the config management UI, selecting the secret reference type, and verifying a dropdown appears populated with available secret names (filtered to show org-scoped and platform-wide secrets). Selecting a secret should populate the value field.

**Acceptance Scenarios**:

1. **Given** an administrator is creating a new config entry, **When** they select the secret reference type, **Then** a dropdown field appears showing available secret names
2. **Given** the dropdown is displaying secrets, **When** administrator views the list, **Then** it includes both org-specific secrets and platform-wide secrets
3. **Given** an administrator selects a secret from the dropdown, **When** the config is saved, **Then** the secret reference is stored correctly
4. **Given** secret list permissions are unavailable, **When** administrator selects secret reference type, **Then** system falls back to manual text input with helpful guidance on naming conventions

---

### User Story 3 - Local Development Secret Management (Priority: P1)

As a developer running the platform locally, I want secrets to be accessible during local development (either from the secure store or a local alternative), so my local workflows behave identically to production without requiring complex setup.

**Why this priority**: Critical for maintaining dev/prod parity and enabling effective local testing. Without this, developers can't fully test workflows that depend on secrets, leading to production-only bugs. This is P1 because it directly impacts developer productivity and code quality.

**Independent Test**: Can be fully tested by running the platform locally and verifying workflows can access secrets for secret reference configurations. Test should work with both actual secure secret access and a local development alternative.

**Acceptance Scenarios**:

1. **Given** a developer has configured the secure store location in their local environment, **When** workflow requests a secret reference configuration, **Then** system authenticates using developer credentials and retrieves the secret from the configured store
2. **Given** a developer is running locally without secure store location configured, **When** system initializes, **Then** it falls back to local secret configuration
3. **Given** a local secret is defined in local configuration, **When** workflow requests that secret, **Then** system uses the local value instead of accessing the secure store
4. **Given** a required secret is missing in both secure store and local configuration, **When** workflow attempts to access it, **Then** system fails with a clear error message indicating which secret is missing and where to configure it
5. **Given** developer credentials are invalid or expired, **When** system attempts to authenticate to secure store, **Then** it falls back to local configuration with a warning message

---

### User Story 4 - Production Secret Resolution (Priority: P1)

As a system operator, I want the platform to automatically authenticate to the secure secret store in production using identity-based authentication, so secrets are securely accessed without storing credentials in application configuration.

**Why this priority**: Security best practice and operational requirement. Identity-based authentication eliminates credential management overhead and reduces attack surface. This is P1 because it's a fundamental security requirement for production deployment.

**Independent Test**: Can be fully tested by deploying to production with identity-based authentication enabled, configuring appropriate access permissions, and verifying workflows can retrieve secrets without any credentials in configuration.

**Acceptance Scenarios**:

1. **Given** the platform is deployed to production with identity-based authentication, **When** system initializes, **Then** it authenticates to the secret store using the system identity without requiring stored credentials
2. **Given** a workflow executes in production, **When** it requests a secret configuration, **Then** secret is retrieved from the secure store using cached authentication
3. **Given** the secret store is temporarily unavailable, **When** workflow attempts to access a secret, **Then** system retries and eventually fails with a clear error indicating unavailability
4. **Given** system identity lacks permissions to access a secret, **When** system attempts retrieval, **Then** it fails with a clear error indicating permission issue

---

### User Story 5 - Secret Lifecycle Management (Priority: P2)

As a platform administrator with platform-wide admin privileges, I want to create, update, and delete secrets through the platform UI, so I can fully manage integration credentials without ever needing to access the secure store directly.

**Why this priority**: Provides complete secret management workflow within the platform. This is P2 because secrets can be managed externally if needed, but full lifecycle management through the UI significantly improves usability and eliminates the need for administrators to learn external tools.

**Independent Test**: Can be fully tested by accessing the secret management UI, creating a new secret, updating its value, deleting it, and verifying all operations succeed and changes are reflected in the secure store.

**Acceptance Scenarios**:

1. **Given** a platform administrator is configuring an integration, **When** they need to store a new API key, **Then** they can create the secret directly in the platform UI and see the plaintext value displayed once for confirmation
2. **Given** a secret exists in the secure store, **When** platform administrator needs to rotate the credential, **Then** they can update the secret value through the UI and see the new plaintext value displayed once for confirmation
3. **Given** a secret is no longer needed, **When** platform administrator deletes it through the UI, **Then** the secret is removed from the secure store and no longer appears in dropdowns or lists
4. **Given** a platform administrator views the secret list after creating a secret, **When** they return to the list view, **Then** secret values are masked (not displayed in plaintext)
5. **Given** a non-admin user attempts to access secret management UI, **When** they try to create/update/delete a secret, **Then** system denies access with a clear message indicating platform admin role is required
6. **Given** a secret name already exists when creating, **When** platform administrator attempts to create it, **Then** system prompts to update existing or choose a different name
7. **Given** platform administrator has previously created a secret, **When** they view that secret in the UI later, **Then** the value is masked and cannot be retrieved through the UI
8. **Given** platform administrator attempts to delete a secret that is currently referenced in active configurations, **When** deletion is requested, **Then** system warns about active references and requires confirmation

---

### User Story 6 - Secure Store Health Monitoring (Priority: P3)

As a platform administrator or developer, I want to view the connectivity status of the secure store, so I can quickly diagnose authentication or network issues without triggering actual secret operations.

**Why this priority**: Improves operational visibility and troubleshooting. This is P3 because the system will fail clearly when secrets are accessed if there's an issue, but proactive health monitoring improves the debugging experience.

**Independent Test**: Can be fully tested by accessing a health/status endpoint or dashboard section, viewing the secure store connectivity status (connected/disconnected), and verifying the status reflects actual connectivity by temporarily blocking access.

**Acceptance Scenarios**:

1. **Given** the platform is deployed with proper secure store configuration, **When** administrator views the health status, **Then** system shows secure store as "connected" with last successful access timestamp
2. **Given** secure store is unreachable or authentication fails, **When** administrator views the health status, **Then** system shows secure store as "disconnected" with error details
3. **Given** developer is running locally, **When** they check health status, **Then** system indicates whether local secure store access is configured and operational
4. **Given** health check detects an issue, **When** administrator views the status, **Then** system provides actionable guidance for resolving the connectivity problem

---

### Edge Cases

- What happens when a secret reference points to a non-existent secret (after checking both org and platform-wide scopes)?
- How does system handle authentication failures in production (identity-based auth not configured)?
- What happens when a config value type is changed from plain text to secret reference but old value remains?
- How does system behave when secret list permissions are denied but retrieval permissions are allowed?
- What happens when a secret value is empty or null?
- How does system handle rate limiting during high-volume secret access?
- What happens when local development is attempted with neither secure store access nor local secret configuration?
- How does system handle circular dependencies if a secret is needed to authenticate to the secret store itself?
- What happens when administrator attempts to update a secret that doesn't exist?
- How does system handle concurrent updates to the same secret by multiple administrators?
- What happens when a secret update fails mid-operation (network interruption)?
- What happens when administrator attempts to delete a secret that doesn't exist?
- How does system behave when secure store delete permissions are denied but read/write permissions exist?
- What happens if a workflow is executing when the referenced secret is deleted?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide a unified configuration retrieval interface that transparently resolves values from either plain configuration or secure secret store based on the configuration type
- **FR-002**: System MUST automatically resolve secret reference configurations by retrieving the referenced secret from the secure secret store
- **FR-003**: System MUST follow org-specific → platform-wide fallback pattern when resolving secrets (try org-scoped secret first, then platform-wide secret)
- **FR-004**: System MUST authenticate to secure secret store in production using identity-based authentication without requiring stored credentials
- **FR-005**: System MUST support local development secret access through either the secure secret store (with developer credentials) or local secret configuration
- **FR-006**: System MUST allow developers to specify secure store location via environment variable or local configuration file
- **FR-007**: System MUST authenticate to secure store in local development using interactive developer credentials when store location is configured
- **FR-008**: System MUST fall back to local secret configuration when secure store location is not configured or authentication fails
- **FR-009**: Configuration management UI MUST display a dropdown of available secrets when administrator selects secret reference type
- **FR-010**: System MUST list secrets filtered to organization scope (show org-specific and platform-wide secrets relevant to the organization)
- **FR-011**: System MUST handle secret list permission failures gracefully by falling back to manual text input for secret references
- **FR-012**: System MUST cache authentication credentials for the duration of workflow execution to avoid repeated authentication overhead
- **FR-013**: System MUST retry secret retrieval operations when encountering transient failures (network errors, rate limiting)
- **FR-014**: System MUST fail workflow execution with clear error messages when required secrets are missing, including guidance on configuration location
- **FR-015**: System MUST validate that secret reference configuration values contain only the secret identifier without scope prefix
- **FR-016**: System MUST log all secret access attempts (without logging secret values) for audit and debugging purposes
- **FR-017**: System MUST prevent exposure of secret values in API responses, logs, or error messages
- **FR-018**: System MUST support retrieving secrets with special characters in names (following secure store naming restrictions)
- **FR-019**: System MUST retrieve the latest version of secrets unless explicitly configured otherwise
- **FR-020**: Configuration management UI MUST allow administrators to create new secrets with name and value
- **FR-021**: Configuration management UI MUST allow administrators to update existing secret values
- **FR-022**: Configuration management UI MUST allow administrators to delete secrets from the secure store
- **FR-023**: System MUST validate secret names against secure store naming rules before creation
- **FR-024**: System MUST restrict secret creation, update, and deletion operations to users with platform-wide admin role
- **FR-025**: System MUST deny secret write operations for non-admin users with clear error messaging
- **FR-026**: System MUST display secret values in plaintext immediately after creation or update for confirmation
- **FR-027**: System MUST mask secret values in all UI views after initial creation/update confirmation
- **FR-028**: System MUST prevent retrieval of previously stored secret values through the UI
- **FR-029**: System MUST warn administrators when attempting to delete secrets that are referenced in active configurations
- **FR-030**: System MUST provide a health check mechanism to validate secure store connectivity and authentication
- **FR-031**: System MUST display secure store connectivity status with actionable error details when issues are detected

### Key Entities

- **Config Entry**: Represents a configuration key-value pair with type information. When type is secret reference, the value field contains only the secret identifier, which is used to locate the secret at runtime
- **Secret Reference**: The link between a config entry and a secure secret. Format is the secret identifier without scope prefix, which gets resolved to org-specific or platform-wide secret during retrieval
- **Secure Secret**: External secret stored securely with organization or platform-wide scope. Contains the actual sensitive value
- **Local Secret**: Development-time secret stored in local configuration for testing without secure store access

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can access any configuration value (string, numeric, structured, or secret) using a single consistent interface without needing to know storage location
- **SC-002**: 100% of secret-dependent workflows execute successfully in local development environment without secure store access (using local configuration)
- **SC-003**: Configuration management UI enables administrators to select from existing secrets with 0 typos in secret reference configuration
- **SC-004**: Secret resolution completes within 100ms after initial authentication (using cached credentials)
- **SC-005**: System handles secure store unavailability gracefully with clear error messages, allowing developers to identify and resolve issues within 5 minutes
- **SC-006**: Zero secret values appear in application logs, error messages, or API responses (verified through log analysis)
- **SC-007**: Local development setup time for secret-dependent workflows reduces to under 2 minutes using local secret configuration
- **SC-008**: Administrators can create, update, or delete a secret through the UI in under 30 seconds
- **SC-009**: Health check endpoint responds within 2 seconds with current secure store connectivity status

## Assumptions

- Secure secret store is provisioned via ARM template deployment alongside the application
- ARM template configures appropriate access policies for managed identity (full read/write/delete permissions)
- System identity has full secret management permissions (get, list, set, delete) in production
- Developers running locally have authentication credentials (interactive login) to access secure store when configured
- Developers can set environment variables or edit local configuration files
- Existing secret reference config type in configuration schema is ready to use
- Secrets follow organization-scoped and platform-wide naming conventions
- Network connectivity between application and secret store is reliable
- Local development uses same organization identifiers as production for consistency
- Secure store location (URL/name) is known and can be documented for local development setup

## Dependencies

- ARM template for infrastructure deployment (includes secure store provisioning and access policy configuration)
- Secure secret store must be provisioned and accessible
- System identity must be configured with full secret management permissions (read, write, delete)
- Existing configuration system with secret reference type
- Authentication library must be available for identity-based authentication

## Out of Scope

- ARM template creation or management (assumed to be provided separately)
- Automated secret rotation scheduling or rotation policies
- Secret versioning UI or version pinning (always use latest version)
- Secret encryption/decryption (handled by secure store)
- Secret backup/recovery procedures
- Integration with external secret management systems beyond the designated secure store
- Multi-region secret replication or failover
- Comprehensive secret access auditing dashboard (basic logging only, full audit trail is secure store responsibility)
- Secret expiration dates or time-to-live management
- Automatic permission configuration (ARM template handles this)
- Secret import/export functionality
