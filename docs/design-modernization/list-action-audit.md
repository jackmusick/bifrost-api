# Platform list-action consistency

User correction, 2026-09-07: review interaction conventions across the platform, not only table widths. Primary names navigate/open records; secondary actions use one overflow menu on desktop and mobile. Preserve meaningful primary task actions (for example Execute) and inline editing Save/Cancel rather than hiding them mechanically.

The read-only audit is a source inventory, not visual acceptance. Parent reconciles its findings against current source; the returned Integrations and Roles rows were stale because those fixes had already landed locally.

| Surface | Current decision / work |
| --- | --- |
| Integrations | Corrected: native name links and shared RecordActionsMenu, desktop/mobile. Mapping rows also use shared overflow for Disconnect/Unlink while retaining primary Configure. Final mapping67447 four theme/width menu/Escape/focus/Configure cases and16 tests59205 pass; parent inspected dark320. |
| Roles | Corrected: shared menu in both layouts, name/count links retained. Four browser menu/edit/delete/cancel cases passed; parent visual review. |
| Users, Forms list, FolderListing | Existing overflow pattern; verify final shared-consumer behavior, no blanket rewrite. |
| Organizations | Reconciled: mobile Edit is the record name primary action, not a duplicate toolbar. Desktop name now a native edit button too. Existing menu retained for dialog opener focus handling. Eight tests/lint and four rendered primary-edit/menu/focus cases passed; parent inspected mobile menu. |
| Config, Knowledge | Implemented shared menus. Config/Knowledge four width/theme primary-open/menu/delete recovery cases passed; parent inspected Config mobile menu and Knowledge HTTP failure dialog. Knowledge HTTP failures now explicitly handled with controlled AlertDialog retry. Whole-route acceptance separate. |
| Tables list | Corrected: name navigation and shared overflow menu in desktop/mobile. Four rendered selection/export/menu/managed-lock/confirmation checks passed. |
| TableDetail, TablesClaimsTab | Corrected: shared overflow menus for document and claim rows/cards. Eleven scoped tests and lint passed; four claim menu/edit/confirmation browser cases passed and parent inspected mobile menus. Four document menu/edit validation, pending guard, and exact-payload failure/retry browser cases passed at 320/1440 light/dark; parent inspected mobile menus. |
| Files PoliciesView | Corrected: shared overflow menu and keyboard-accessible policy identity edit entry in both layouts. Four scoped tests/lint passed; four 320/1440 light/dark rendered menu/Escape-focus/editor cases passed, parent inspected mobile menu. |
| Events source list | Corrected: shared EventSourceActions menu in mobile cards/desktop rows; primary links and active switches retained. Six tests/lint passed; four rendered list/delete retry cases passed and parent inspected mobile menu. |
| Event source detail | Now shares EventSourceActions with list rows/cards; explicit Active/Refresh retained. Four actual-route keyboard/edit/delete recovery cases79038 passed, parent screenshots reviewed. |
| Event SubscriptionsTable | Terra implemented shared menu/resource-name edit and mobile title/menu alignment, preserving status and delete recovery; scoped tests/lint and rendered cases reported. Parent reviewed menu and error screenshots/source; fixed mobile edit dialog footer visibility, four final rendered failure/retry cases passed. |
| ApplicationListSurface | Corrected: shared Settings/Code/Delete menu in cards/table, native name open button, managed restrictions retained. Removed redundant Version column (repeated publication status). Ten scoped tests/lint passed; four width/theme browser cases including both desktop views passed, parent inspected mobile/desktop menus. |
| WorkflowListSurface | Corrected: shared History/editor/scope menu, name opens history and Execute stays explicit. Eight scoped tests and lint passed; four browser width/theme cases (both desktop views) passed and parent inspected. Status badge colors now semantic tokens. Endpoint/missing-file actions moved from pointer-only badges into the menu; two keyboard callback tests and four synthetic rendered menu/dialog checks passed. Parent inspected mobile recovery menu. |
| ConfigOverridesTab | Shared overflow menu with DropdownMenuItem for delete; inline editing retained. Scoped tests/lint passed, actual-route mobile screenshot parent-reviewed. |
| ModelPricingList, HmacSecretList | Secondary actions use shared menu and DropdownMenuItem; primary edit/activation retained. Scoped tests/lint passed and parent reviewed actual-route captures. Pricing mobile menu moved beside identity; four additional rendered long-value/keyboard/name-edit cases17492 passed and parent inspected. |

Use `components/common/RecordActionsMenu.tsx` for shared trigger/portal behavior. Page-specific menu children own labels, permissions, callbacks and confirmations. Keyboard opening, Escape focus return, no row-click propagation, and narrow/wide rendered proof are required for each corrected surface.

Focused destructive actions now use DropdownMenuItem variant="destructive" rather than a text-color override:20 items across18 files corrected. Source-detail focused color assertion79038 passed in both themes and widths; parent inspected.
