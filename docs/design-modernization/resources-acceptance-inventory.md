# Resources Acceptance Inventory

Scope: Entity Management, MCP Servers, Integrations, and Event Sources/Events. This is a source-and-test inventory only. No suites were run for this pass.

## Entity Management

Primary UI sources:

- `client/src/pages/EntityManagement.tsx`
- `client/src/components/entity-management/EntityCard.tsx`
- `client/src/components/entity-management/EntityListToolbar.tsx`
- `client/src/components/entity-management/EntityAssignmentPanel.tsx`
- `client/src/components/entity-management/EntityAssignmentSheet.tsx`
- `client/src/components/entity-management/deleteEntities.ts`
- `client/src/components/editor/WorkflowDeactivationDialog.tsx`

Concrete actions in source:

- Load and normalize workflows, forms, agents, apps, organizations and roles.
- Search, type/org/access/usage filter, clear filters, sort by name/date/type, reverse sort.
- Select individual records, select all visible non-managed records, clear selection.
- Show dependency relationships and enter/clear relationship-filter mode.
- Open the dependency graph dialog.
- Change organization scope by button/drop target or drag/drop, with review confirmation.
- Change access to authenticated, clear roles, or assign a role, with review confirmation.
- Delete one entity or a bulk selection.
- Resolve workflow delete conflicts by force deactivation or replacement mapping.
- Exclude solution-managed records from selection, drag, assignment and deletion while keeping dependency viewing available.

Existing browser evidence:

- `docs/design-modernization/entity-management-review.md` records UI-verified acceptance for bulk delete recovery, workflow dependency resolution, managed records, assignment recovery, full-page filters/collection recovery, relationship graph, compact assignment sheet, drag-to-organization, and restricted-access gating.
- The recorded browser fixtures are intercepted/synthetic for mutations. They prove UI control state, request sequencing, retry behavior, focus/viewport behavior and absence of protected reads in restricted sessions; they do not prove real backend persistence through the browser.

Existing component evidence:

- `client/src/components/entity-management/EntityCard.test.tsx`: dependency action remains direct; managed records keep dependencies and lose destructive menu.
- `client/src/components/entity-management/EntityAssignmentPanel.test.tsx`: assignment review snapshot, duplicate-submit guard, failure retry, keyboard access assignment.
- `client/src/components/entity-management/DropTargets.test.tsx`: button and drag selections route to review and block while busy.
- `client/src/components/entity-management/EntityListToolbar.test.tsx`: mixed/hidden selections, sort controls and search recovery.
- `client/src/components/entity-management/EntityCollectionStatus.test.tsx`: missing versus cached collection failures and retry.
- `client/src/components/entity-management/FilterPopover.test.tsx`, `RelationshipFilterBanner.test.tsx`, `DependencyGraphDialog.test.tsx`, `DeleteConfirmDialog.test.tsx`: filter independence, relationship recovery, graph sizing, delete confirmation/pending behavior.

Backend/API evidence:

- Entity Management dispatches to existing workflow/form/agent/application update and delete endpoints rather than a page-specific API. Relevant backend behavioral coverage is split across those resource suites and manifest/role-sync tests, for example `api/tests/e2e/platform/test_git_sync_local.py` role assignment/access-level/org-scope cases and `api/tests/unit/test_sync_ops.py`.

Explicit gaps:

- No committed Playwright spec exercises the Entity Management page with real create/assign/delete persistence against live services.
- Backend authorization is not proven by the Entity Management UI fixtures; the review ledger explicitly treats restricted-access browser proof as UI gating.
- Drag/drop and workflow conflict recovery are covered by synthetic browser fixtures and component tests, not by committed `client/e2e` tests.

## MCP Servers And Connections

Primary UI sources:

- `client/src/pages/MCPServers.tsx`
- `client/src/pages/MCPServerDetail.tsx`
- `client/src/pages/MCPConnectionEdit.tsx`
- `client/src/components/mcp/MCPServerForm.tsx`
- `client/src/pages/mcp/components/NewConnectionDialog.tsx`
- `client/src/pages/mcp/components/ServerConnectionList.tsx`
- `client/src/pages/mcp/components/ServerSettingsSummary.tsx`
- `client/src/pages/mcp/components/ConnectionToolCatalog.tsx`

Concrete actions in source:

- List server templates, search by name/URL, refresh server list and connection counts.
- Open New Server, discover OAuth metadata, switch to manual override, choose OAuth flow, submit server creation.
- Navigate to server detail, switch Connections/Server settings/Manifest tabs.
- Refresh server detail and connection list.
- Delete server with cascade warning and retry after failure.
- Create a per-org connection with initial client credentials.
- Edit connection credentials, availability flags, OAuth/client-credentials activation, tool catalog enablement, catalog refresh, disconnect and delete.

Existing browser evidence:

- `docs/design-modernization/mcp-list-acceptance.md` records UI-verified `/mcp-servers` list, create, discovery and manual-override behavior across themes/widths.
- `docs/design-modernization/mcp-connection-acceptance.md` records UI-verified connection editor read recovery, credential masking/editing, save/partial failure, catalog refresh, disconnect, activation, OAuth start and delete.
- `docs/design-modernization/PROGRESS.md` records MCP server detail evidence for tabs, metadata bounds, manifest explanation, initial/cached read recovery, navigation and delete retry.
- These browser runs used intercepted mutations, synthetic URLs and stubbed authorization windows. They prove UI behavior and payloads, not real OAuth exchange or real server/connection persistence through the browser.

Existing component evidence:

- `client/src/components/mcp/MCPServerForm.test.tsx`: draft retention and pending lock on failure, client-credentials discovery with manual overrides, failed-discovery guidance and labelled OAuth fields.
- `client/src/pages/mcp/components/NewConnectionDialog.test.tsx`: organization lookup failure/empty states and disabled create.
- `client/src/pages/mcp/components/ConnectionToolCatalog.tsx` has behavior covered through connection editor browser evidence; no direct sibling test was found in this pass.

Backend/API evidence:

- `api/tests/e2e/mcp/test_mcp_parity.py`: MCP tool DTO signature parity and REST-backed CRUD roundtrips for roles, configs, organizations, integrations/mappings and workflows.
- `api/tests/e2e/mcp/test_mcp_tool_access_matrix.py`: agent-scoped MCP HTTP tool visibility/execution for platform admin, org user, unauthorized user, provider org user and cross-org denial.
- `api/tests/e2e/mcp/test_mcp_scoped_lookups.py` and `api/tests/unit/services/mcp_server/test_tool_access.py`: scoped lookup and tool-access service behavior.
- These tests cover the MCP protocol/tool layer. They are not UI server-template lifecycle tests.

Explicit gaps:

- No committed `client/e2e` spec was found for creating/editing/deleting MCP server templates or connections through the real UI.
- Real OAuth consent, token exchange, callback completion and remote catalog discovery remain outside current UI acceptance.
- The server detail Manifest tab states per-server export is future enhancement; import from manifest on the list is disabled in source.

## Integrations

Primary UI sources:

- `client/src/pages/Integrations.tsx`
- `client/src/pages/Integrations/IntegrationList.tsx`
- `client/src/pages/IntegrationDetail.tsx`
- `client/src/components/integrations/CreateIntegrationDialog.tsx`
- `client/src/components/integrations/IntegrationDeleteDialog.tsx`
- `client/src/components/integrations/IntegrationOverview.tsx`
- `client/src/components/integrations/IntegrationMappingsTab.tsx`
- `client/src/components/integrations/IntegrationDefaultsDialog.tsx`
- `client/src/components/integrations/OrgConfigDialog.tsx`
- `client/src/components/integrations/ConfigOverridesTab.tsx`
- `client/src/components/integrations/EntitySelector.tsx`
- `client/src/components/integrations/EntityIdSourcePicker.tsx`
- `client/src/components/integrations/IntegrationTestPanel.tsx`

Concrete actions in source:

- List integrations, search, switch card/table layout, select visible integrations, export selected/all, import, refresh.
- Create integration, edit integration, confirm removed schema fields, delete integration.
- Open detail, edit shell metadata/schema/provider settings, delete integration from detail.
- Configure default integration values.
- Configure organization-specific mapping values and configuration overrides.
- Search mappings, choose provider entity, enter manual entity ID, auto-match, accept/reject suggestions, accept all, clear suggestions.
- Create/update/delete mappings, connect/refresh/disconnect per-mapping OAuth, configure default OAuth, refresh/reconnect default OAuth.
- Run integration test requests and generate SDK scaffolding/config.

Existing browser evidence:

- `docs/design-modernization/integrations-list-acceptance.md`: UI-verified `/integrations` list, create/edit/import dialogs, selection/read/delete behavior with intercepted mutations.
- `docs/design-modernization/integration-detail-review.md`: UI-verified detail route covering header, mapping layout, overview, provider/read/match/save/retry, partial batch retry, defaults/config editing, overrides, org config recovery, OAuth picker/callback and protected-route gating.
- `docs/design-modernization/list-action-audit.md`: shared overflow action parity for integration list and mapping secondary actions.
- Committed Playwright:
  - `client/e2e/integration-cards.admin.spec.ts`: real description/logo/table navigation coverage on the list.
  - `client/e2e/integration-mapping-acceptance.admin.spec.ts`: `[MAPPING-01] add and edit organization mappings persist after reload and search`; seeds integration/orgs through `api-fixture`, edits mappings through UI, reloads and asserts `/api/integrations/{id}` persistence.
  - `client/e2e/per-mapping-oauth.admin.spec.ts`: mapping table renders and Connect button opens authorize URL.

Existing component evidence:

- `client/src/components/integrations/CreateIntegrationDialog.test.tsx`: create payload/retry, edit confirmation, data-provider read retry, save recovery and field-removal confirmation.
- `IntegrationMappingsTab.test.tsx`: row rendering, entity selector, auto-match controls, search, manual input-on-blur, configure dialog entry, unlink/disable states, OAuth connect/refresh/disconnect controls.
- `IntegrationDefaultsDialog.test.tsx`, `OrgConfigDialog.test.tsx`, `ConfigOverridesTab.test.tsx`, `ConfigFieldInput.test.tsx`, `OverrideValueEditor.test.tsx`: config field types, defaults, override save/delete, invalid JSON and reset behavior.
- `IntegrationOverview.test.tsx`, `IntegrationTestPanel.test.tsx`, `IntegrationTestResult.test.tsx`, `EntitySelector.test.tsx`, `EntityIdSourcePicker.test.tsx`, `AutoMatchControls.test.tsx`, `MatchSuggestionBadge.test.tsx`: overview OAuth actions, test panel, entity selection and matching behaviors.

Backend/API evidence:

- `api/tests/e2e/api/test_integrations.py`: CRUD, mappings CRUD, SDK data, OAuth authorize URL behavior, integration config defaults/overrides/SDK precedence/secrets and authorization denials.
- `api/tests/e2e/oauth/test_per_mapping_connect.py`: per-mapping authorize, disconnect, refresh, empty entity IDs and entity-id-source backfill/clear behavior.
- `api/tests/e2e/platform/test_cli_integrations.py` and `test_cli_integrations_external.py`: CLI integration surfaces and external-user global secret/token restrictions.
- `api/tests/e2e/mcp/test_mcp_parity.py`: MCP integration and mapping roundtrip through REST bridge.
- `api/tests/e2e/platform/test_git_sync_local.py`: integration manifest import, schema/config preservation, mapping identity and cross-instance reconciliation.

Explicit gaps:

- Real external OAuth consent/token exchange is not proven by UI tests.
- Most rich detail-route UI recovery evidence is in design-modernization browser ledgers with intercepted mutations, not committed Playwright specs.
- `GenerateSDKDialog` has component coverage for generation ordering/success, but no committed browser lifecycle spec was found.

## Event Sources And Events

Primary UI sources:

- `client/src/pages/Events.tsx`
- `client/src/pages/events/EventSourceCard.tsx`
- `client/src/components/events/EventSourceActions.tsx`
- `client/src/components/events/EventSourceDetail.tsx`
- `client/src/components/events/CreateEventSourceDialog.tsx`
- `client/src/components/events/EditEventSourceDialog.tsx`
- `client/src/components/events/SubscriptionsTable.tsx`
- `client/src/components/events/CreateSubscriptionDialog.tsx`
- `client/src/components/events/EditSubscriptionDialog.tsx`
- `client/src/components/events/EventsTable.tsx`
- `client/src/components/events/EventDetailDialog.tsx`
- `client/src/components/events/DeliveriesTable.tsx`
- `client/src/components/events/DynamicConfigForm.tsx`

Concrete actions in source:

- List event sources, search, filter by status tab, filter by organization scope, refresh.
- Create webhook, schedule, topic and Microsoft Graph event sources.
- Edit source metadata/config, schedule cron/timezone/overlap, webhook rate limits and dynamic provider config.
- Toggle source active state from list or detail.
- Delete source from list or detail.
- Open source detail, copy webhook URL, refresh source/events, resubscribe Graph provider source.
- Manage subscriptions: add, edit, toggle active, delete.
- Browse events, search event types, open deep-linked event inspector.
- Inspect metadata/deliveries, retry failed deliveries, send not-delivered deliveries and copy delivery errors.

Existing browser evidence:

- `docs/design-modernization/events-acceptance.md` records UI-verified list/detail/inspector routes: list shell/read/delete recovery, shared source actions, source creation for schedule/webhook/topic/Graph schema, source activation, detail delete/copy/resubscribe, live events, subscriptions, edit dialogs, dynamic Graph context and event inspector delivery recovery.
- Committed Playwright:
  - `client/e2e/event-delivery-acceptance.admin.spec.ts`: `[EVENT-01 desktop] local webhook event shows successful workflow delivery and execution outcome`; real local webhook event, delivery and execution outcome path.
  - `client/e2e/event-source-graph.admin.spec.ts`: Graph tenant/user loading after visible retry and Graph context/resubscribe UI.
- Design-led browser evidence uses intercepted writes for source mutations and provider operations; committed delivery acceptance supplies stronger real end-to-end evidence for local webhook delivery.

Existing component/page evidence:

- `client/src/pages/Events.test.tsx`: mobile/desktop list shells, detail routing, cached read retry and delete failure retry.
- `CreateEventSourceDialog.test.tsx`: validation, webhook payload, rate limit controls, organization context, schedule branch, topic branch, source switching and metadata recovery.
- `EditEventSourceDialog.test.tsx`: prefill/update, overlap policy, rate-limit fields, cron validation race and save retry.
- `EventSourceDetail.test.tsx`: populated metadata, active toggle, delete confirmation, non-admin controls hidden, Graph identity/resubscribe and read recovery.
- `SubscriptionsTable.test.tsx`, `CreateSubscriptionDialog.test.tsx`, `EditSubscriptionDialog.test.tsx`: subscription create/edit/toggle/delete/retry behavior and input mapping.
- `EventsTable.test.tsx`, `EventDetailDialog.test.tsx`, `DeliveriesTable.test.tsx`: events empty/populated/search/deep-link/read recovery, inspector metadata/delivery recovery, retry/send permissions and per-row failure recovery.
- `DynamicConfigForm.test.tsx`: static/dynamic fields, organization context, dependent values, field associations and retry.

Backend/API evidence:

- `api/tests/e2e/api/test_builtin_events.py`: workflow, delivery retry-exhausted and integration built-in events run subscribers.
- `api/tests/unit/test_bifrost_events_sdk.py`: SDK event emit endpoint/scope/error behavior.
- `api/tests/unit/routers/test_events_webhook_creation.py`: provider subscription starts after webhook source commit and failed provider subscription removes provisional source.
- `api/tests/e2e/platform/test_git_sync_local.py`: event source manifest import, topic event type, organization updates, event subscription natural-key import and full-manifest import order.

Explicit gaps:

- Real Microsoft Graph/provider subscription lifecycle and remote webhook provider behavior are not proven; browser evidence stubs/intercepts those operations.
- Most source create/edit/delete activation UI paths are accepted via design browser fixtures and component tests, not committed Playwright specs.
- Event inspector authorization and permanently deleted event restoration are explicitly outside the recorded UI acceptance.

## Cross-Cutting Notes

- Existing design-modernization acceptance documents record many browser handle IDs and parent screenshot reviews, but most are not committed tests. They are useful evidence for the modernization effort, yet they should not be treated as durable CI coverage.
- Committed browser coverage is strongest for Integration mapping persistence and local webhook event delivery.
- MCP server/connection and Entity Management lifecycle actions have good component/backend coverage plus design-led UI fixture evidence, but lack committed real-UI persistence specs.
- Backend/API coverage is broad for integrations, events, MCP tool access and manifest sync. It does not automatically prove that every current UI action wires the correct accessible control to a live persisted mutation.
