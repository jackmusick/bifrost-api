# Existing form designer acceptance

Status: UI Verified. Scope: `/forms/:formId/edit`. Runtime/embed execution and shared component-wide schema compatibility remain separate.

The designer retains its fields/preview layout and keyboard reorder controls. Field, metadata, context and workflow-test dialogs now have bounded mobile scrolling with accessible actions. Existing-form loading errors cannot expose an empty editable canvas; cached failures retain edits. Saving locks the canvas and header until completion, then either focuses a retained-draft retry or returns to Forms.

| Area | Evidence |
| --- | --- |
| Loading/recovery | Current60723: four custom-purple light/dark320/1440x600 initial form/workflow failures and retries, disabled launch until metadata recovery, local reorder retained through cached failure/retry. |
| Metadata | Current49143 and footer20639: four matching cases clear description/launch workflow, change org to Global, reopen retained metadata and correct explicit-null request payload. Footer checks prove Save/Cancel viewport bounds. Parent inspected dark320. |
| Optional persistence | Database route tests37649 pass explicit-null clearing and omitted-field preservation for description/launch/default parameters/allowed query parameters. API quality83129 passes. |
| Role selection | Final67422: eight matching replace/clear cases for loaded roles, revised selections/reopen, exact PATCH role_ids and no additive role mutations. Parent inspected light320. Initial46445 used a role-name trigger assertion; corrected to the actual count trigger plus per-option checked state. |
| Save | Current65660/final16406: four held PATCH500/pending canvas/header protection, retained reordered fields, focused failure/retry/equal payload and destination. Parent inspected dark320. |
| Field controls | Browser42190: four field edit/required/file choices/context/local update retention cases. Twelve FieldConfigDialog tests29889 cover field validation/payload/conditional controls. |
| Context/launch | Final83875: four six-parameter launch pending/failure/draft retry, actual entered payload, results/context bounds. Parent inspected narrow dialogs. |
| Quality | Six FormBuilder tests87629 and scoped lint/full TypeScript86579 pass; touched-source diff check passes. |

Existing forms hydrate role_ids from FormPublic and save replacements through the existing PATCH contract. New-form partial role-save recovery remains separate and retains its prior behavior. Source-reviewed update_form bulk replacement handles role_ids=[], while omitted role_ids leaves assignments untouched; existing API e2e role tests cover that contract but were not rerun in this UI pass.

All browser mutations are synthetic. No customer forms, roles or workflow runs changed. The platform-admin route guard and backend solution-managed write guard remain; this UI acceptance does not replace application-wide access tests, complete shared schema/runtime compatibility checks or release gates.

## Responsive workspace follow-up

The editor workspace is centered and capped at 1400px, including its heading and
actions. Desktop uses a 16–20rem palette plus a flexible field canvas. Narrow
layouts stack the palette and fields, retain the collapsible palette and touch
controls, and keep the field workspace usable. This applies to editing, not just
Preview. Live checks at 2560×1440 and 390×844 verified bounded width, no horizontal
overflow, opening field settings, and switching to Preview. Existing form-builder
and field-panel interaction tests passed.


## Settings controls and editors follow-up

Field settings use the shared Switch for query-parameter opt-in and boolean
defaults. Descendant button sizing excludes switch and checkbox roles. Other
boolean configuration controls were aligned in integrations, event configuration,
scheduling, MCP connections, repository creation, and workflow keys. Selection
checkboxes and runtime form/v1 checkbox semantics are retained.

Available Context uses the shared JSON syntax renderer and active branding tokens.
Agent instructions use the shared Tiptap editor and continue to persist Markdown;
solution-managed instructions remain read-only. Live debug review verified mobile
switch geometry and highlighted context, plus creating an agent with bold
instructions, reading back Markdown, and deleting the synthetic test agent.
Focused component tests, TypeScript, and scoped lint passed.
