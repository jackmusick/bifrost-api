# Feature Specification: OAuth Helper for Integrations and Workflows

**Feature Branch**: `004-oauth-helper-for`
**Created**: 2025-10-12
**Status**: Draft
**Input**: User description: "OAUTH Helper for integrations and workflows. This would essentially allow the system to accept OAUTH requests to a unique endpoint and then save the response as a secret. We'd store a list of OAuth connections. The app would then have a scheduled job that ran, looked for ones that were expiring and refreshed them. This way workflows and integrations had an easy way to do something like get_config('azure_csp_oauth') without needing to worry about interactive auth. So the process would be that you would create an OAUTH config with basic information and save. Then, you'd need to fill in information about it (like in Postman). You'd get some instructions about what URL to put in. This URL would probably be something like http://client_url/oauth/integration_id (likely the page we're on currently). We'd be able to click connect launching the oauth process and once complete, it would return here with the information. We'd have a status like Waiting on callback then Testing connection…, then Completed or Failure with a reason. At this point the full oauth config is saved. If this is something other than client credential (which obviously wouldn't need a connect button), we'd have a job that was scheduled to refresh the token."

## User Scenarios & Testing

### User Story 1 - Create OAuth Connection Configuration (Priority: P1)

A system administrator needs to set up an OAuth connection so that workflows and integrations can authenticate with external services without requiring manual intervention. They create a new OAuth configuration by providing basic information such as the connection name, OAuth flow type, client credentials, and authorization endpoints.

**Why this priority**: This is the foundational capability that enables all other OAuth functionality. Without the ability to create and configure OAuth connections, the entire feature has no value.

**Independent Test**: Can be fully tested by creating an OAuth configuration through the interface, saving it, and verifying it persists correctly. Delivers immediate value by establishing the foundation for OAuth connections.

**Acceptance Scenarios**:

1. **Given** no existing OAuth configurations, **When** administrator creates a new OAuth configuration with valid connection details, **Then** the configuration is saved and appears in the list of OAuth connections
2. **Given** administrator is creating an OAuth configuration, **When** they specify the OAuth flow type (authorization code, client credentials, refresh token), **Then** the system displays appropriate fields for that flow type
3. **Given** administrator has entered OAuth configuration details, **When** they save the configuration, **Then** system provides the callback URL they need to register with the OAuth provider
4. **Given** administrator creates an OAuth configuration, **When** they view the configuration details, **Then** sensitive information like client secrets are masked but configuration metadata is visible

---

### User Story 2 - Complete Interactive OAuth Authorization (Priority: P1)

After creating an OAuth configuration, the administrator needs to complete the OAuth authorization flow for flows that require user interaction (authorization code flow). They click a "Connect" button which launches the OAuth authorization process, redirecting to the external provider's authorization page. After granting permissions, they are redirected back with the authorization response.

**Why this priority**: This is the second critical step that makes OAuth connections usable. Without completing authorization, the connection cannot be used by workflows or integrations.

**Independent Test**: Can be fully tested by initiating the OAuth flow from a saved configuration, completing authorization with the external provider, and verifying the connection status changes to "Completed". Delivers value by establishing working OAuth credentials.

**Acceptance Scenarios**:

1. **Given** an OAuth configuration requiring interactive authorization, **When** administrator clicks "Connect", **Then** they are redirected to the OAuth provider's authorization page
2. **Given** administrator has authorized the application at the OAuth provider, **When** they are redirected back to the callback URL, **Then** the system receives and securely stores the OAuth tokens
3. **Given** OAuth callback has been received, **When** system processes the response, **Then** status changes from "Waiting on callback" to "Testing connection"
4. **Given** system is testing the connection, **When** test succeeds, **Then** status changes to "Completed" and connection becomes available for use
5. **Given** system is testing the connection, **When** test fails, **Then** status changes to "Failure" with a descriptive reason explaining what went wrong
6. **Given** OAuth configuration uses client credentials flow, **When** administrator views the configuration, **Then** no "Connect" button is displayed as interactive authorization is not needed

---

### User Story 3 - Access OAuth Credentials in Workflows (Priority: P1)

A developer building a workflow or integration needs to authenticate with an external service. Instead of handling OAuth flows themselves, they simply reference the OAuth connection by name, and the system provides valid, current credentials automatically.

**Why this priority**: This is the primary business value of the feature - enabling workflows and integrations to use OAuth without complex authentication logic. This makes the feature immediately useful.

**Independent Test**: Can be fully tested by creating a simple workflow that retrieves OAuth credentials using a connection name, and verifying it receives valid credentials. Delivers value by simplifying integration development.

**Acceptance Scenarios**:

1. **Given** a completed OAuth connection exists, **When** workflow code requests credentials using the connection name, **Then** system returns valid OAuth credentials
2. **Given** workflow requests OAuth credentials, **When** the access token is still valid, **Then** system returns the current token without refreshing
3. **Given** workflow requests OAuth credentials, **When** connection does not exist or is in failed state, **Then** system returns an error indicating the connection is unavailable

---

### User Story 4 - Automatic Token Refresh (Priority: P2)

The system needs to ensure OAuth tokens remain valid over time without manual intervention. A scheduled background process checks OAuth connections for tokens approaching expiration and automatically refreshes them using refresh tokens when available.

**Why this priority**: While critical for production use, this can initially be handled manually or with shorter-lived workflows. This makes it P2 rather than P1, as basic OAuth functionality works without it.

**Independent Test**: Can be fully tested by creating an OAuth connection with a short-lived token, waiting for the token to approach expiration, and verifying the system automatically refreshes it before it expires. Delivers value by ensuring uninterrupted service.

**Acceptance Scenarios**:

1. **Given** OAuth connection has a refresh token, **When** scheduled job detects token will expire soon, **Then** system uses refresh token to obtain new access token
2. **Given** token refresh succeeds, **When** new tokens are obtained, **Then** system updates stored credentials and maintains "Completed" status
3. **Given** token refresh fails, **When** refresh token is invalid or expired, **Then** system updates connection status to "Failure" with descriptive reason
4. **Given** multiple OAuth connections exist, **When** scheduled job runs, **Then** system efficiently checks and refreshes only connections with expiring tokens
5. **Given** OAuth connection uses client credentials flow without refresh tokens, **When** token expires, **Then** system automatically requests new token using client credentials

---

### User Story 5 - Manage and Monitor OAuth Connections (Priority: P2)

Administrators need to view, edit, and delete OAuth connections, as well as monitor their status. They can see a list of all configured connections, their current status, last refresh time, and other relevant metadata. They can also manually trigger reconnection if a connection fails.

**Why this priority**: While important for operational management, the basic OAuth flow can work without comprehensive management features initially. These are quality-of-life improvements.

**Independent Test**: Can be fully tested by performing various management operations (view list, edit configuration, delete connection, manually reconnect) and verifying each works correctly. Delivers value by providing operational control.

**Acceptance Scenarios**:

1. **Given** multiple OAuth connections exist, **When** administrator views the connections list, **Then** they see connection name, status, OAuth provider, and last activity for each
2. **Given** administrator selects an OAuth connection, **When** they view details, **Then** they see full configuration and connection history
3. **Given** OAuth connection is in "Failure" state, **When** administrator clicks "Reconnect", **Then** system initiates a new OAuth authorization flow
4. **Given** administrator edits OAuth configuration, **When** they change connection parameters, **Then** system marks connection as requiring reconnection
5. **Given** administrator attempts to delete an OAuth connection, **When** deletion confirmation is shown, **Then** system displays warning with recommendation to search for `get_oauth_connection('connection_name')` in @workflows/workspace/ before proceeding
6. **Given** administrator attempts to delete a config secret, **When** the secret is referenced by an OAuth connection, **Then** system blocks deletion and shows error message indicating which OAuth connection(s) reference it

---

### Edge Cases

- What happens when OAuth callback URL receives an error response from the provider (user denied access, invalid scope, etc.)?
- How does system handle OAuth connections when the external provider is temporarily unavailable during token refresh?
- What happens when multiple workflows simultaneously request credentials from the same OAuth connection?
- How does system handle OAuth configurations where refresh tokens are not provided or supported?
- What happens when administrator changes OAuth configuration while workflows are actively using the connection?
- How does system handle callback URLs that include state parameters for security validation?
- What happens when token refresh occurs while a workflow is actively using the current token?
- How does system handle OAuth connections with very short token lifetimes (less than scheduled job interval)?
- What happens when the same OAuth provider is used for multiple different connections (same provider, different scopes or accounts)?
- What happens when workflows using deleted OAuth connections are executed?

## Requirements

### Functional Requirements

- **FR-001**: System MUST allow administrators to create new OAuth connection configurations with connection name, OAuth flow type, client ID, client secret, authorization URL, token URL, and requested scopes
- **FR-002**: System MUST generate and provide unique callback URLs for each OAuth connection configuration
- **FR-003**: System MUST support multiple OAuth flow types including authorization code, client credentials, and refresh token flows
- **FR-004**: System MUST securely store OAuth credentials (access tokens, refresh tokens, client secrets) with encryption at rest
- **FR-005**: System MUST handle OAuth callback requests at the designated endpoint and process authorization codes or tokens
- **FR-006**: System MUST track connection status through states: "Not Connected", "Waiting on callback", "Testing connection", "Completed", and "Failure"
- **FR-007**: System MUST test OAuth connections after receiving credentials by making a test request to validate functionality
- **FR-008**: System MUST provide descriptive failure reasons when OAuth connections fail during setup or refresh
- **FR-009**: System MUST allow workflows and integrations to retrieve OAuth credentials by connection name
- **FR-010**: System MUST run scheduled background process every 15 minutes to check for expiring OAuth tokens and refresh them proactively
- **FR-011**: System MUST automatically refresh access tokens using refresh tokens when tokens will expire within the next 30 minutes
- **FR-012**: System MUST handle client credentials flow without requiring interactive authorization or "Connect" button
- **FR-013**: System MUST allow administrators to view list of all OAuth connections with current status
- **FR-014**: System MUST allow administrators to edit OAuth connection configurations
- **FR-015**: System MUST allow administrators to delete OAuth connections
- **FR-016**: System MUST allow administrators to manually trigger reconnection for failed OAuth connections
- **FR-017**: System MUST display deletion warning when administrators attempt to delete OAuth connections, with recommendation to search for usage in workflow code before proceeding
- **FR-018**: System MUST prevent deletion of config secrets that are referenced by active OAuth connections
- **FR-019**: System MUST mask sensitive credential information in user interfaces while displaying configuration metadata
- **FR-020**: System MUST log all OAuth connection lifecycle events for audit purposes

### Key Entities

- **OAuth Connection Configuration**: Represents a configured OAuth connection including connection name, OAuth provider details (authorization URL, token URL), OAuth flow type, client credentials, requested scopes, callback URL, and current status. Links to stored credentials when authorization is complete.

- **OAuth Credentials**: Represents the stored OAuth tokens including access token, refresh token (if available), token expiration time, token type, and granted scopes. Associated with a specific OAuth connection configuration.

- **Connection Status**: Represents the current state of an OAuth connection including status value ("Not Connected", "Waiting on callback", "Testing connection", "Completed", "Failure"), last status change timestamp, failure reason (if applicable), and last successful token refresh timestamp.

- **OAuth Callback Event**: Represents incoming OAuth callback requests including authorization code or tokens, state parameter for validation, timestamp, source OAuth connection configuration, and processing result.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Administrators can create and authorize a new OAuth connection in under 3 minutes (excluding external provider authorization time)
- **SC-002**: Workflows can retrieve OAuth credentials in under 100 milliseconds
- **SC-003**: System successfully refreshes 99% of OAuth tokens before expiration with no manual intervention required
- **SC-004**: 95% of OAuth authorization flows complete successfully on first attempt
- **SC-005**: System supports at least 100 concurrent OAuth connections with different providers
- **SC-006**: Token refresh process completes in under 2 seconds per connection
- **SC-007**: Administrators can identify failed OAuth connections and their failure reasons within 30 seconds of viewing the connections list
- **SC-008**: Zero credential exposure incidents - all sensitive OAuth data remains encrypted and masked

### Assumptions

- OAuth providers conform to standard OAuth 2.0 specification
- System has persistent storage available for OAuth configurations and credentials
- System can make outbound HTTPS requests to OAuth providers
- System has a publicly accessible callback URL endpoint that OAuth providers can reach
- Administrators have necessary permissions and credentials from OAuth providers before creating connections
- Token expiration times provided by OAuth providers are accurate
- Token refresh timing: scheduled job runs every 15 minutes and refreshes any tokens expiring within the next 30 minutes
- Deletion behavior: system warns administrators about potential workflow impacts but does not automatically detect or disable dependent workflows since workflows are filesystem-based Python scripts without metadata
- Workflows will fail at runtime with clear error messages if they reference deleted OAuth connections
- OAuth connection testing uses a lightweight health check or profile endpoint to validate credentials
