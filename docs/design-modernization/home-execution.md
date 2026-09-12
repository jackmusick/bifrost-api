# Home and execution experience

Status: implemented on the design-system modernization debug branch; not merged.

The user approved a shared Home for apps, forms and agents, personal favorites and collections, admin-curated collections, improved app opening, and an execution/history workbench. Preserve the current Bifrost identity, custom branding, resource permissions, V1 runtime, and existing navigation to resources. Keep the debug stack available; do not merge.

## Delivery checklist

- [x] Persist personal favorites and collections, with admin-managed organization collections. Collection membership never grants resource access.
- [x] Select collection icons from the existing Lucide library.
- [x] Build Home with pinned resources, collections, search/type filtering and explicit organization context. Keep existing management pages.
- [x] Improve app opening with truthful brand-aware loading and recoverable errors.
- [x] Build a bounded execution workspace with readable plain streaming logs, search/filtering, follow/pause, and input/result inspection. Do not fabricate workflow steps.
- [x] Add optional History preview while retaining direct execution navigation, compact controls and shared pagination.
- [x] Verify relevant API permissions, component interactions and desktop/mobile rendered behavior; record evidence and limitations.

## Interaction contract

Home launches work; History finds previous or active runs; execution explains their activity and outcome. Personal organization is available to ordinary authenticated users. Shared curation follows existing administrative privileges. Resources removed or inaccessible must not leak metadata through collections. Organization context must remain visible when a provider browses across customers.

Desktop execution and History are bounded workspaces; mobile uses focused full-width content. Result is the default experience, followed by Input and Logs. Log messages wrap with timestamps secondary; logs occupy space only when selected. Structured events may supply richer views only when the recorded data supports them. Motion represents activity, not invented progress.

Approved concepts: Home `exec-04191ae9-0afe-4ae3-ab38-5e2e386c62a4.png`, History `exec-ffa284d4-eff1-44be-ab9c-e47b3a482bd4.png`, execution `exec-21e7f13b-154f-4fed-865e-6b4c6ad5b6cb.png`, in the session's generated-images directory. Use real shared components rather than reproduce incidental inconsistencies in generated images.

## Using the experience

Home is at `/`; the administrative dashboard remains at `/dashboard`. Star an app, form, or chat-enabled agent to pin it. Create a collection, select a Lucide icon, choose resources, and reorder its contents. Users can manage personal collections; administrators can also curate shared collections for an organization or the global workspace. Existing management routes remain available.

Home uses the existing resource repositories to enforce access. Collection membership never changes permissions. Inaccessible entries are omitted from responses, retained on ordinary edits, and cannot be exposed by changing a collection's audience. Embedded sessions cannot use workspace curation APIs. Favorites and recent launches persist per user.

Execution uses the same Result, Input, Logs content in the full page and preview. Result is selected by default; changing tabs remains a deliberate choice during streaming. Running results show truthful status and available activity. Metadata is collapsible, and an absent log stream reserves no column. History row/name clicks open the preview on desktop and the existing detail drawer on mobile; the preview retains an explicit full-page link. Shared pagination remains outside the bounded table scroller.

## Verification — 2026-09-08

- Client TypeScript and full ESLint passed; API Pyright and Ruff passed with zero errors or warnings.
- 222 targeted client tests passed across Home, execution, History, and theme behavior.
- App-opening and router regression checks: 17 tests passed.
- Home API unit checks: 10 passed; API end-to-end checks: 3 passed.
- DTO/contract checks: 64 passed.
- Browser tests passed for collection creation/editing/persistence and actual incremental execution logs through completion, including mobile log search and clear.
- Debug browser review at 1440×1000 and 390×844: Home, collection editor, execution, History preview, and light theme. No page errors on the final pass; no horizontal execution overflow. History table width matched its scroller (666px), and pagination ended at y=964 inside the 1000px viewport.
- Local screenshots: `/tmp/bifrost-design-review/{home-final-desktop,home-final-mobile,home-final-light,collection-final-mobile,execution-final-desktop,execution-final-mobile,history-final-preview}.png`.

Limits: this is targeted feature validation, not a fresh whole-platform or production V1 acceptance run. The existing debug Covi Portal compatibility fixture remains available; its underlying V1 runtime was not rewritten. Collection icons are a searchable curated Lucide set, not arbitrary uploads. Recent-resource tracking begins with launches from Home.

## Deployment

Apply migration `20260908_home_collections` before serving the new Home APIs. It has been applied to the debug stack. Keep this branch unmerged pending user review.


## Home navigation follow-up — 2026-09-08

The approved Home mock is implemented in the existing shell. Workspace navigation is Home, Chat, and History; accessible collections follow as shortcuts. Management links are separated for platform administrators, with the existing Data, Platform, and Reports destinations retained. Dashboard is available through an administrator-only Home/Dashboard route tab, with its protected route unchanged.

Search and category counts stay above the desktop scroll region. Choosing a category, searching, or opening a collection brings the results first and resets the content scroll position. The unfiltered overview shows up to three pinned shortcuts (with View all for additional pins), collections, a compact catalog preview grouped by Apps, Forms, and Agents. Each group shows at most two entries and links to its complete catalog. Browse all explicitly opens the full paginated catalog; the recent-work section is removed. Home shares Dashboard’s 1,400px maximum width. Cards are the default; list view and sorting by name or recent launch remain available. Collection order is preserved unless explicitly sorted.

Whole resource cards open their resource; favorite controls remain separate. Mobile retains full-width content and collection links close the navigation drawer. Existing resource APIs and V1 app runtime behavior are unchanged.


Follow-up validation:
- `npm --prefix client test -- src/pages/Home src/components/layout/WorkspaceTabs.test.tsx src/components/layout/Sidebar.test.tsx`: 29 tests passed.
- `./test.sh client e2e e2e/home.admin.spec.ts`: setup and Home journey passed, including Dashboard navigation, category/search discovery, sidebar creation, persistence, editing, and deletion.
- Full client ESLint and TypeScript checks passed before the final collection-heading spacing adjustment; final affected component tests and type/lint checks cover that adjustment.
- Debug browser checks at 1440×1000 and 390×844 reported no page errors or horizontal mobile overflow. Category results begin at y=281 on desktop. Mobile collection navigation closes the drawer; sidebar collection creation opens and dismisses correctly.
- Screenshots: `/tmp/bifrost-design-review/workspace-{desktop,filtered,mobile,mobile-filtered,mobile-collection}.png`.


## Result-first and catalog refinement — 2026-09-08

This iteration replaces the log-first split pane with a shared Result/Input/Logs presentation. Short results and failures size to their content; long results scroll within available desktop height. While active, Result includes the latest actual log message and a View logs action. Result objects use result-field wording rather than input-parameter labels. Manual tab selection is preserved while a run updates.

History now opens previews from ordinary desktop row/name clicks. The explicit full-page link and modified-link browser gestures remain available. Pagination fixes retain current rows only when the page cursor/offset changes within the same scope and filters; they cover History executions, History logs, Audit, and table documents. See [pagination audit](pagination-audit.md).

Validation:
- Combined scoped run: 40 test files, 275 tests passed (Home, execution components/details, History/components, Audit, table documents, and pagination hooks/guards).
- Debug browser: Home measured 1,400px wide at a 2,560px viewport; no horizontal overflow at 390px.
- Debug execution review covered completed structured results, failed results, Result/Input/Logs switching, mobile layout, and desktop preview opening.
- A held History continuation request retained the same table DOM element and disabled Next; no page errors were reported.
- Review screenshots: `/tmp/bifrost-design-review/home-refined-wide.png`, `result-first-desktop.png`, `result-first-mobile.png`, `result-first-preview.png`, and `result-first-failed.png`.

- Live test command `./test.sh client e2e e2e/home.admin.spec.ts e2e/executions-realtime.admin.spec.ts` passed: setup plus both journeys. Streaming starts with Result selected, supports switching to Logs, preserves that choice at completion, reveals the completed Result on request, and supports mobile log filtering/clearing.
- Final client TypeScript and full ESLint checks passed. No full-platform or production acceptance run was performed in this focused iteration.

## Execution disclosure layout follow-up

The full page and preview now omit the extra bordered execution-content wrapper. Tabs and expanded metadata use natural document flow inside the existing page/preview scroller: expanding More details cannot shrink the selected panel to zero height. Bottom spacing belongs to that scroll content. The activity metadata and selected content share an 84rem maximum-width wrapper.

History retains date grouping with larger, higher-contrast date rows. Home centers its search icon relative to the actual input height and uses the shared OrganizationSelect, including searchable organizations and All/Global scope semantics.

Verification: 49 targeted component tests passed. A live debug browser check expanded metadata, switched through all three tabs, confirmed each panel remained visible and the disclosure followed it, checked mobile overflow, and measured zero vertical offset between the search icon and input centers. Screenshots: `/tmp/bifrost-design-review/execution-unboxed-expanded.png` and `execution-unboxed-bottom.png`.

The live streaming spec passed with the new expanded-metadata/tab-switching regression. Client TypeScript and scoped ESLint passed.

### Collection dialog follow-up

The collection editor owns one scrollable form body. The dialog shell clips overflow,
its header and action footer stay fixed, and the icon/resource lists participate in
that same scroll area. This avoids competing scrollbars and removes the outer
padding that previously compounded the footer spacing. Selected items and search
results show the object's icon with app/form/agent fallbacks.

Delete follows AppInfoDialog's placement and destructive ghost styling: left of
Cancel/Save on desktop, below the paired actions on mobile. Role, table, workflow,
and user edit dialogs do not expose Delete in their save footer; deletion is a
separate action for those entities. Collection deletion retains its explicit
confirmation and does not delete its resources.

Reviewed the live debug dialog at 1440×1000 and 390×844: exactly one vertical
scroll area, visible actions at the bottom, and a 1px border between the footer
bottom and dialog edge. Home E2E now checks these scrolling and footer bounds
while editing a collection at desktop and mobile widths.

### History picker and live activity follow-up

OrganizationSelect now opens at the greater of 20rem or its trigger width,
clamped to the viewport gutter. This shared default covers narrow History
filters as well as wider form controls. Live History inspection measured a
176px trigger and a 320px popup.

The Result tab's running state now shows a reusable ExecutionActivityFeed of
actual messages in order, with proportional text and a quiet timeline. It follows
new messages until the user scrolls back; Follow latest activity resumes following.
View logs retains access to levels, timestamps, search, and technical details.
The same feed is used by full execution details and the embedded preview.

On re-entry, a stream's default Running status could overwrite terminal API data
in the query cache. Terminal cached statuses now reject nonterminal stream
updates; cached trigger re-entry also bypasses the new-run fetch delay. Regression
tests cover both paths with a real QueryClient for the status overwrite.

Validation: organization picker/component tests, activity follow/pause test,
execution detail regressions, TypeScript and scoped lint; Docker streaming E2E
passed and now checks that multiple messages appear in the Result activity feed
before opening technical logs. Live desktop and mobile feed screenshots show
wrapped messages without horizontal overflow.

### Running status motion and History stability

Running badges now use a rotating conic border highlight in the configured primary
color. The overlay is absolute and paint-only; reduced-motion keeps it static.
History reserves space for the conditional Cancel action and for duration/start
values, with tabular digits for timestamps. These columns no longer contract as
an execution completes or clock values change. This keeps workflow/status columns
from moving when the Cancel action disappears.

### Shared dropdown sizing contract

Searchable dropdowns use `PopoverContent variant="picker"`. The primitive owns
one default: at least 20rem wide, at least the trigger width when there is room,
and capped to the viewport gutter. WorkflowSelector, OrganizationSelect, generic
comboboxes/multicomboboxes, role selectors, user/app/workflow/agent editor pickers,
dynamic configuration options, and MCPToolPicker use this contract instead of
copying trigger-width classes. Future searchable pickers should use this variant.
Content overrides remain available for intentionally wider pickers. Action menus
use intrinsic content width capped to the viewport, independent of icon triggers.
Ordinary Select already uses the trigger as a minimum rather than a fixed width.

### Compact History actions

Removed the desktop Preview column: row and workflow-title clicks already open
the execution preview. The remaining Cancel slot uses a 32px desktop control
with reduced cell padding; smaller screens retain the 44px touch target. Space stays
reserved after completion so the table does not shift. Day-group column spans
were reduced to match the removed column.

### Collection scope consistency

CollectionEditor uses OrganizationSelect for audience selection, including the
shared picker width, organization search, scope icons, and selected-state styling.
OrganizationSelect now supports opt-in `showPersonal` with the exported
`PERSONAL_SCOPE` value; existing organization-only callers are unaffected.
CollectionEditor translates it back to `shared: false, organization_id: null`.
Shared scope selection is still restricted to platform admins, and audience
changes retain the existing resource compatibility filtering.

### Agent private scope and New Agent feedback

AgentSettingsTab opts into OrganizationSelect's personal choice. Selecting Only me
maps to `access_level: private`, hides access-level and role controls, and clears
role selections. Regular users start private in their own organization; admins
can select private or return to Global/an organization to configure shared access.
Private remains hidden by default for scope-picker callers that do not opt in.

New Agent previously compared `actionFailure?.id` to an absent agent ID; both were
undefined, incorrectly rendering the status-update failure banner before any
mutation. The feedback now requires an actual failed action.

Client regression tests cover private defaults, hidden sharing controls, restoring
shared controls, the submitted private access level, and absence of the false
creation error. A live debug create verified private access plus an owner ID and
removed the synthetic agent afterward.

Updating shared agents to private now assigns the current user as owner and removes
agent role grants. Updating an already-private agent preserves its existing owner,
including when a platform admin edits it. Returning to shared access clears the
private owner. Existing non-admin publishing restrictions remain in place.

### Empty collections and lookup loading

Home uses `isVisibleCollection`: a collection is visible
when it has accessible resources or the viewer can edit it. Managers retain empty
collections so they can populate them. Readers do not see shared collections with
no usable resources. Collections are available only through Home tabs.
Home retains a single Create a collection CTA
in its empty state; no show-empty toggle is needed.

Removed visible stacks of lookup-loading text above agent and user edit forms.
Those status messages remain available to assistive technology; lookup controls
retain their loading feedback and errors still expose retry actions. The agent
form no longer adds top padding for loading-only notices.

## Unified catalog and execution refinement (September 10)

The approved desktop/mobile concept replaces Home's pinned section, collection cards, and category previews with one paginated catalog. Collection navigation filters the same resources; overflow collections remain reachable through More. Pins appear once, first in the default ordering. Search ranks exact/prefix/title matches before description matches and uses pins as a tie-breaker. Explicit name, recent, and collection ordering remain available. Type and organization filters retain existing access semantics; collections do not grant access. Collections appear only as Home tabs; sidebar shortcuts are removed on all routes.

Resource cards use larger title hierarchy, existing uploaded logos and library icons, and distinct app/form/agent icon tones in both themes. Cards remain whole-card launch targets with a separate accessible pin action. On mobile the catalog uses two columns with wrapping names, descriptions and organization identity. The Dashboard remains accessible to administrators.

Execution preserves the shared full-page/drawer inspector and Result/Input/Logs contract. Running activity uses a wrapping chronological message stream with secondary timestamps and newest-message emphasis. Scrolling upward pauses following; the existing follow control returns to current activity. A rotating angular mask exposes the active branding gradient around one border, and reduced motion disables its loop. The separate metadata strip does not duplicate the animation. Completion removes the active frame and the redundant Result heading/count, retaining the actual generic result renderer and copy/tree controls. No workflow stages, percentages or result summaries are inferred from log text.

Verification for this refinement is scoped to Home, sidebar collection navigation, execution components and their browser consumers. The earlier complete candidate gate remains evidence for its original SHA, not for subsequent visual edits. Review screenshots and commands are recorded with the implementation handoff.

Scoped checks for this refinement: 222 component tests passed across the Home/sidebar/execution group; the navigation test received a TypeScript-only query-option correction afterward. Browser verification covered the Home catalog, launch/pin persistence, collection CRUD and access boundaries, execution details/back/rerun/cancel/drawer, real streaming, public form execution, and chat attachments. The broader affected browser pass completed 17 tests successfully; its one stale chat-heading assertion was restored and the complete chat/execution group then passed 9/9 without retries. The original Home layout tests were updated to test the single catalog and selected-collection edit controls rather than removed presentation sections. Production client build passed. Changed-file ESLint reported no errors (the review seeder retains its existing stdout-JSON warning).

Desktop/mobile review evidence is under `/tmp/bifrost-home-execution-v2-final`; real running screenshots are retained in the scoped Playwright execution artifacts. Debug form submission and webhook delivery use the existing owned review pack. These checks do not claim a new full pre-PR/nightly run.

Final confirmation: application TypeScript check (`tsc --noEmit -p tsconfig.app.json`) passed; the corrected collection-navigation test passed; ordinary-user denied-route recovery back to Home passed (2 browser tests including setup). The debug review pack completed both actual form and webhook executions. No merge was performed.

### Shared variable viewers and collection tab actions

PrettyInputDisplay applies the same framed surface, branded field labels, quiet type metadata, and responsive label/value layout to both inputs and results. VariablesTreeView groups expanded children and separates root fields while retaining per-value copy and keyboard expansion. Execution streaming is unchanged by this refinement.

Collection tabs expose Edit and Delete only for editable collections through a context menu (right-click, Shift+F10, or touch long-press). Delete opens the existing confirmation flow. Desktop native dragging and Move left/right reorder the personal view; All remains fixed first. Selecting an overflow collection appends it to the visible tabs so its actions remain reachable.

Collections appear only as Home tabs; no sidebar shortcuts are rendered on any route. Order is stored per account in this browser. Reordering a filtered scope preserves other collections' positions. It does not change shared collection ownership, content, grants, or other users' layouts, and does not yet sync between browsers/devices.

### Shared resource cards and Settings refinement

Home, Apps, Forms, Agents, and Workflows now consume ResourceCatalogCard.
It owns the icon/title/action/description/footer layout, stretched primary
click target, keyboard focus, and equal row heights. Catalog overflow menus
retain editing, history, preview, and MCP copy actions. Form launch eligibility
and Solution-managed restrictions remain intact. Agent catalog cards keep
their management destination and fleet metrics; Home agents still open Chat.

Settings navigation and content now share one bounded frame, with a tinted
navigation surface and brand-colored active state. Embeddings and Usage no
longer impose independent content widths. Mobile navigation stays collapsible,
and visited panel drafts remain mounted. Form Builder back navigation sits
beside the title and save returns to the originating Solution when present.

Verified with scoped unit commands: Settings.test.tsx AIEmbeddingSettings.test.tsx
AIUsageSettings.test.tsx (39 tests); ResourceCatalogCard.test.tsx ResourceCard.test.tsx
ResourceIcon.test.tsx FormListSurface.test.tsx WorkflowListSurface.test.tsx
FormBuilder.test.tsx (25 tests); Applications.test.tsx FleetPage.test.tsx
AgentMcpCopyButton.test.tsx (34 tests). All passed using ./test.sh client unit --.
Scoped ESLint and npm run tsc passed. Live Playwright coverage passed for
forms-acceptance.admin.spec.ts, forms.user.spec.ts, home-catalog-acceptance.admin.spec.ts,
and workflows.admin.spec.ts using ./test.sh client e2e. The workflow test
was corrected to click the resource title after the dedicated launch button
was removed, then passed in its scoped rerun. Desktop/mobile cards, menus,
Settings navigation, and Form Builder back navigation were reviewed live.
The full pre-PR gate was not rerun for this branch refinement; no merge.
