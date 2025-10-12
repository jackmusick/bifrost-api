# Feature Specification: Integration Mapping Framework

**Feature Branch**: `003-integration-mapping-framework`
**Created**: 2025-10-11
**Status**: Draft
**Input**: User description: "Integration mapping framework with organization discovery and workflow APIs - extending integrations to enable organization mapping by exposing standard functions like list_organizations, with UI for matching orgs to IDs and workflow methods for get_integration_mapping and set_integration_mapping"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enable Integration for Organization Mapping (Priority: P1)

An MSP admin enables an integration (like HaloPSA) for organization mapping, allowing the system to discover and display available external organizations from that integration.

**Why this priority**: This is foundational - without discovering external organizations, administrators cannot create mappings. This provides immediate value by showing what's possible to connect.

**Independent Test**: Can be fully tested by configuring an integration with a list_organizations function and verifying the system recognizes it as "mapping-enabled" and can fetch and display the list of external organizations.

**Acceptance Scenarios**:

1. **Given** an integration implements the list_organizations function, **When** admin views integrations, **Then** the integration is marked as "Integration Mapping Enabled"
2. **Given** a mapping-enabled integration, **When** admin clicks "Discover Organizations", **Then** system displays list of external organizations with ID and name
3. **Given** discovery is successful, **When** admin views results, **Then** organizations are searchable and selectable for mapping

---

### User Story 2 - Map Organization to External System (Priority: P1)

An MSP admin maps their customer organization to an external system organization (e.g., maps "Acme Corp" to HaloPSA customer ID "12345"), enabling workflows to access that external system on behalf of the organization.

**Why this priority**: This is the core value - creating the mapping that makes multi-tenant workflows possible. Without this, the framework provides no benefit.

**Independent Test**: Can be fully tested by creating a mapping between an MSP organization and an external organization ID, then verifying the mapping is persisted and retrievable.

**Acceptance Scenarios**:

1. **Given** an organization without mappings, **When** admin creates new integration mapping with external org ID, **Then** mapping is saved and displayed
2. **Given** integration supports discovery, **When** admin selects external org from dropdown, **Then** external org name and ID are auto-populated
3. **Given** integration doesn't support discovery, **When** admin manually enters external org ID, **Then** system accepts and validates the input
4. **Given** a saved mapping, **When** admin views organization details, **Then** all integration mappings are displayed with external org names

---

### User Story 3 - Retrieve Mapping in Workflow (Priority: P1)

A workflow developer retrieves an organization's integration mapping to authenticate and interact with the external system on behalf of that organization.

**Why this priority**: This completes the P1 value chain - the ability to use mappings in workflows is what makes the feature useful in production. Without this, mappings are just data with no action.

**Independent Test**: Can be fully tested by calling get_integration_mapping in a workflow and verifying it returns the correct external organization ID and metadata for the given integration.

**Acceptance Scenarios**:

1. **Given** organization has HaloPSA mapping, **When** workflow calls get_integration_mapping('halopsa'), **Then** returns mapping with external org ID and name
2. **Given** organization has no mapping for an integration, **When** workflow calls get_integration_mapping('unmapped_integration'), **Then** raises clear error indicating no mapping exists
3. **Given** organization has multiple mappings for same integration, **When** workflow calls get_integration_mapping without mapping_id, **Then** raises error requesting specific mapping_id
4. **Given** organization has multiple mappings, **When** workflow calls get_integration_mapping with specific mapping_id, **Then** returns correct mapping

---

### User Story 4 - Create Mapping from Workflow (Priority: P2)

A workflow automatically creates an integration mapping when provisioning a new customer, eliminating manual mapping setup for automated onboarding scenarios.

**Why this priority**: This enables automation but is not required for basic functionality. Manual mapping creation works for most scenarios, so this is an enhancement.

**Independent Test**: Can be fully tested by calling set_integration_mapping in a workflow and verifying the mapping is created and retrievable via get_integration_mapping.

**Acceptance Scenarios**:

1. **Given** workflow creates new organization, **When** workflow calls set_integration_mapping with external org ID, **Then** mapping is created and persisted
2. **Given** mapping already exists, **When** workflow calls set_integration_mapping with new external org ID, **Then** existing mapping is updated
3. **Given** workflow provides invalid external org ID, **When** set_integration_mapping is called, **Then** validation error is raised with clear message
4. **Given** workflow creates mapping, **When** subsequent workflow calls get_integration_mapping, **Then** returns the workflow-created mapping

---

### User Story 5 - View and Manage Integration Mappings (Priority: P2)

An MSP admin views all integration mappings for an organization in a dedicated UI tab, with ability to edit, test, or remove mappings.

**Why this priority**: This provides management capabilities but the core value (P1) is creating and using mappings. Management is important but secondary to functionality.

**Independent Test**: Can be fully tested by navigating to an organization's Integration Mappings tab and performing CRUD operations on mappings.

**Acceptance Scenarios**:

1. **Given** organization has multiple integration mappings, **When** admin views Integrations tab, **Then** all mappings are displayed with integration name, external org, and status
2. **Given** admin selects a mapping, **When** clicking Edit, **Then** dialog opens with current mapping details pre-filled
3. **Given** admin modifies mapping, **When** clicking Save, **Then** mapping is updated and changes are reflected immediately
4. **Given** admin selects a mapping, **When** clicking Delete, **Then** confirmation dialog appears and mapping is removed upon confirmation

---

### User Story 6 - Test Integration Connection (Priority: P3)

An MSP admin tests an integration mapping to verify it's configured correctly and can successfully connect to the external system.

**Why this priority**: This is a quality-of-life feature. While helpful for troubleshooting, it's not required for the mapping to function - workflows will naturally fail if the mapping is incorrect, providing error feedback.

**Independent Test**: Can be fully tested by clicking "Test Connection" button and verifying the system attempts connection and displays success or failure result.

**Acceptance Scenarios**:

1. **Given** valid integration mapping, **When** admin clicks Test Connection, **Then** system connects to external system and displays success message
2. **Given** invalid mapping credentials, **When** admin clicks Test Connection, **Then** system displays error message with troubleshooting guidance
3. **Given** external system is unavailable, **When** admin clicks Test Connection, **Then** system displays timeout error with retry option

---

### Edge Cases

- What happens when an external organization is renamed or deleted in the integration system? (Mapping shows stale data until manually updated)
- How does system handle integration that supports discovery but API is rate-limited? (Implement caching and show cached results with timestamp)
- What happens when workflow tries to use mapping for deactivated organization? (Raise error indicating organization is inactive)
- How does system handle duplicate external org IDs across different integrations? (Allow - they're scoped by integration name)
- What happens when set_integration_mapping is called with integration that doesn't exist? (Validation error with list of available integrations)
- How does system handle workflow creating mapping without proper permissions? (Permission check raises authorization error)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow integrations to declare support for organization mapping via supports_org_mapping property
- **FR-002**: System MUST allow mapping-enabled integrations to expose list_organizations function that returns external organization IDs and names
- **FR-003**: System MUST display integrations that support organization mapping with "Integration Mapping Enabled" indicator in UI
- **FR-004**: Administrators MUST be able to create mappings between MSP organizations and external organization IDs through UI
- **FR-005**: System MUST support both automatic discovery (dropdown selection) and manual entry of external organization IDs
- **FR-006**: System MUST allow multiple mappings per organization for the same integration (e.g., multiple M365 tenants)
- **FR-007**: System MUST persist mappings with organization ID, integration name, external org ID, external org name, and metadata
- **FR-008**: Workflows MUST be able to retrieve integration mappings via get_integration_mapping(integration_name, mapping_id?)
- **FR-009**: Workflows MUST be able to create or update integration mappings via set_integration_mapping(integration_name, external_org_id, metadata?)
- **FR-010**: System MUST raise clear error when workflow requests mapping that doesn't exist
- **FR-011**: System MUST raise error when workflow requests integration mapping without specifying mapping_id when multiple mappings exist
- **FR-012**: System MUST validate external organization IDs before saving mappings
- **FR-013**: Administrators MUST be able to view all integration mappings for an organization in dedicated UI tab
- **FR-014**: Administrators MUST be able to edit, delete, and test existing integration mappings
- **FR-015**: System MUST cache discovered organizations for reasonable duration to reduce API calls to external systems
- **FR-016**: System MUST allow administrators to manually refresh cached organization lists
- **FR-017**: System MUST restrict mapping management to users with appropriate permissions (canManageConfig)
- **FR-018**: System MUST log all mapping creation, modification, and deletion actions for audit purposes

### Key Entities

- **Integration Definition**: Represents an integration type (HaloPSA, Microsoft 365, etc.) with properties indicating if it supports organization mapping and what functions it exposes
- **Organization Mapping**: Links an MSP organization to an external organization ID with integration name, external org name, mapping metadata, active status, and audit fields (created by, created at, updated at)
- **External Organization**: Represents an organization from external integration with ID, name, and optional metadata returned by list_organizations function
- **Mapping Metadata**: Flexible key-value data attached to mapping for integration-specific configuration (e.g., API endpoints, regional settings)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Administrators can create an integration mapping in under 2 minutes from discovering external organizations to saving the mapping
- **SC-002**: Workflows can retrieve integration mappings and successfully authenticate with external systems on first attempt for 95% of properly configured mappings
- **SC-003**: Discovery of external organizations completes within 10 seconds for integrations with up to 1000 external organizations
- **SC-004**: System correctly handles and displays error messages for 100% of failed mapping operations (creation, retrieval, validation)
- **SC-005**: Administrators can view and understand all integration mappings for an organization at a glance without additional documentation
- **SC-006**: 90% of integration mapping use cases require zero custom code - handled entirely by standard framework
- **SC-007**: New integrations supporting organization mapping can be enabled without modifying core platform code

## Assumptions *(include when making design decisions)*

- External organization IDs are stable identifiers that don't change frequently in integration systems
- Integration credentials are managed separately through existing Key Vault system
- Administrators have knowledge of which external organization IDs correspond to their customers
- Most integrations will support organization discovery, but manual entry fallback is needed for exceptions
- Workflow execution context already has access to organization information to determine which mappings to load
- Integration API rate limits are reasonable and caching for 1 hour is acceptable for discovered organizations
- Permission system already exists and canManageConfig permission is appropriate for mapping management
- Multiple mappings per integration are edge case but important enough to support from beginning

## Dependencies *(include when clear)*

### Existing Systems

- Organizations and permission management system
- Workflow execution engine and OrganizationContext
- Key Vault for storing integration credentials
- Table Storage for persisting mapping data
- Audit logging system for tracking changes

### New Capabilities Required

- Integration interface contract defining supports_org_mapping and list_organizations
- Dual-indexed storage tables for mapping lookups (by organization and by integration)
- UI components for Integrations tab on Organizations page
- Workflow context methods for get_integration_mapping and set_integration_mapping
- Caching layer for discovered external organizations

## Out of Scope *(clarify what's not included)*

- Building specific integrations (HaloPSA, NinjaRMM, etc.) - only the framework
- Real-time synchronization of external organization changes
- Automatic mapping suggestions based on organization name matching
- Bulk mapping operations (will be future enhancement)
- Integration health monitoring and alerting
- Mapping templates or copy functionality
- Historical tracking of mapping changes beyond audit log
- UI for browsing all mappings across all organizations (global view)
