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

Desktop execution and History are bounded workspaces; mobile uses focused full-width content. Plain logs are a primary experience, with timestamps secondary and wrapping messages retaining available width. Structured events may supply richer views only when the recorded data supports them. Motion represents activity, not invented progress.

Approved concepts: Home `exec-04191ae9-0afe-4ae3-ab38-5e2e386c62a4.png`, History `exec-ffa284d4-eff1-44be-ab9c-e47b3a482bd4.png`, execution `exec-21e7f13b-154f-4fed-865e-6b4c6ad5b6cb.png`, in the session's generated-images directory. Use real shared components rather than reproduce incidental inconsistencies in generated images.

## Using the experience

Home is at `/`; the administrative dashboard remains at `/dashboard`. Star an app, form, or chat-enabled agent to pin it. Create a collection, select a Lucide icon, choose resources, and reorder its contents. Users can manage personal collections; administrators can also curate shared collections for an organization or the global workspace. Existing management routes remain available.

Home uses the existing resource repositories to enforce access. Collection membership never changes permissions. Inaccessible entries are omitted from responses, retained on ordinary edits, and cannot be exposed by changing a collection's audience. Embedded sessions cannot use workspace curation APIs. Favorites and recent launches persist per user.

Execution puts plain logs first: wrapping messages, search, severity filtering, copy/download, follow/pause, and a separate input/output inspector. Completion reveals output unless the user explicitly chose another inspector tab. Activity animation is indeterminate and respects reduced motion. History offers an explicit preview action alongside direct navigation; its shared pagination remains outside the bounded table scroller.

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
