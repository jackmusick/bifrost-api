# Knowledge review

Status: UI Verified. Coverage42 Verified/22 In progress.

## Delete recovery and current composition (2026-09-07)

Previous goal turn made progress: Files accepted. Extracted Knowledge delete confirmation into page-local KnowledgeDeleteDialog using the established controlled pending/error pattern. It identifies the target by key/id, has synchronous duplicate protection, pending Cancel/Escape guard, focused/scrolled inline server detail, same-target retry and stable Add Document focus fallback. Knowledge handler retains existing endpoint and HTTP detail parsing, closes only on success. Six Knowledge tests1235 and scoped lint/full TypeScript2312 pass.

knowledge-delete-current.cjs62517 passes4 actual-route light/dark320/1440 custom-purple cases: cards/table inverse, no document overflow, current overflow menu, named target, pending500, focused error and visible retry, one retry then focus restoration. Parent inspected dark320 list and deletion failure. All knowledge API mutations intercepted; no real documents deleted.

Parent composition finding: mobile header, search, two filters, export/import and selection controls occupy most of the first viewport before the document content. Improve filter/bulk presentation to prioritize reading without hiding necessary context. Bulk scope remains inline in1100-line page: no pending dismissal/selector lock, server failures toast only, replacement confirmation auto-closes. Extract into page-local reusable implementation with captured selection/destination and recovery. Drawer also has replacement-confirmation lifecycle to inspect.

Existing scripts knowledge-flow-check.cjs and knowledge-recovery-check.cjs now cover agent/role namespace assignment rather than the Knowledge page; do not rely on their names. config-knowledge-verify.cjs has actual /knowledge flow but old auth-execution.json and combined Config path; adapt only its relevant current code. Knowledge read/list/drawer/pagination/import-export/scope/permissions acceptance remains open.

All parent processes terminal; diff check passes. No blocker, goal active. Next bulk scope and mobile toolbar composition.

## Knowledge bulk scope recovery (2026-09-07)

Previous turn was progress: delete dialog extracted and verified. New page-local KnowledgeScopeDialog captures selected IDs when opened, owns destination/pending/conflict/error state, guards duplicate submissions and Escape/cancel while pending, and keeps409 replacement confirmation in the same dialog. Replacement retains the chosen destination and explicit destructive action; Back allows revising the target. Server/network errors remain focused inline with original selection and target retained. Success clears selection, refetches documents and restores stable Add Document focus (the Change Scope opener disappears when selection clears).

Knowledge page no longer owns bulk mutation state/request/inline dialogs; existing PATCH endpoint and document_ids/scope/replace semantics preserved. Six Knowledge tests29595 and scoped lint/full TypeScript18169 pass. Final scoped lint81432 running after replacing disappearing scope-button focus target with createRef.

knowledge-scope-current.cjs45666 passes4 custom-purple light/dark320/1440 actual-route cases: selected record, Global target,409 transition, locked destination, pending Escape/Back, focused500, visible Replace and exact identical forced-retry payload, success and Add Document focus. Parent inspected dark320 replacement error. No real knowledge scope or document changed; requests intercepted. Route remains In progress, overall41 Verified/23 In progress.

Next: mobile toolbar/filter/bulk composition to bring document content higher; then drawer/read/filter/pagination/import/export/permissions acceptance. No blocker; goal active.

Final scoped lint81432 passes. All parent handles terminal; diff check passes. Inventory136 page modules/362 feature components/53 primitives; route count unchanged.

## Knowledge compact filters (2026-09-07)

Previous goal turn was progress: bulk scope extracted and verified. New page-local KnowledgeFilters keeps search visible alongside a44px Filters toggle below1024, collapses namespace/organization controls, reports active count and retains values when collapsed. Desktop keeps the original visible controls. Shared SearchBox now has an explicit accessible name; mobile placeholder is shorter to avoid clipping. No filtering/query semantics changed.

Six Knowledge tests46734 pass. Scoped lint passes; full TypeScript2530 running at this entry. Initial browser98897 passes4 custom-purple light/dark320/1440 actual-route cases: mobile filter visibility/count/retained selection, desktop inverse, no document overflow and first record top<520px (previously about590px). Parent inspected dark320; content preview now appears in initial viewport. Final33679 running after placeholder correction and adding explicit keyboard Enter activation of Filters.

Coverage41 Verified/23 In progress. Knowledge remains open for drawer/read/import/export/pagination/permissions acceptance. Next source gap: KnowledgeDocumentDrawer replacement dialog still auto-closes using legacy destructive styles and does not guard pending replacement separately; inspect and improve with same draft-preserving recovery contract. Goal active, no blocker.

Final full TypeScript2530 and4-case keyboard/filter browser33679 pass. Parent inspected final dark320 shorter-search composition. All parent handles terminal; diff check passes. Inventory137 page modules/362 feature components/53 primitives.

## Knowledge drawer save/replacement recovery (2026-09-07)

Previous turn made progress: compact filters. KnowledgeDocumentDrawer now synchronously guards duplicate save requests, focuses/scolls save errors and keeps replacement confirmation open while pending. Replacement errors appear in the confirmation, preserving draft and explicit retry; Cancel/Escape are disabled during request. Removed legacy destructive overrides. Drawer uses shared return-focus hook with stable Add Document fallback.

Initial4 drawer tests92614 and source lint/full TypeScript87713 pass. Real-editor knowledge-replace-current.cjs70034 passes4 custom-purple light/dark320/1440 edit409/held replacement500/identical forced retry cases preserving metadata/content; parent inspected dark320 confirmation error. Final focus assertion rerun19171 passes all4. Combined10 tests64235 initially had one failure: older Knowledge test queried the previous mobile placeholder. Updated to accessible Search documents role/name; final10 tests98335 pass. Source lint/full TypeScript30291 passes.

knowledge-save-current.cjs86237 is running8 ordinary create/edit cases: real Tiptap draft, pending guard, focused error, visible Save, identical POST/PUT retry and return focus. Its inherited log wording says replacement but fixture is ordinary save and mode loop covers both. All requests synthetic intercepted; no real documents changed.

Knowledge remains In progress, coverage41 Verified/23 In progress. Remaining: current read/error/empty/list namespace-scope-search/pagination/import-export/permission acceptance consolidation. No blocker; goal active.

Final ordinary-save browser86237 passes all8 create/edit cases. Parent inspected dark320 create error with draft retained and fixed Save/Cancel footer. All parent handles terminal; diff check passes.

## Acceptance checkpoint (2026-09-07)

Current import checks pass four light/dark320/1440 custom-brand cases: malformed JSON recovery, retained valid selection, HTTP500 and retry. Fresh restricted-user checks pass four cases with access denial and no knowledge API reads. Current list recovery checks pass four cases: independent namespace/document retry, preserved cached rows/search/selection on refresh failure, pagination offset50 and reset0 on search, true filtered empty state, selected export exact synthetic ID and all export empty ID list. Read recovery63307 passes four real-editor cases: failed load prevents editing/saving, retry restores original content and Cancel performs no write.

Parent inspected dark320 import error, retained-list refresh error and document read failure. Prior create/edit/scope/delete/filter evidence above plus final ten focused tests, lint and TypeScript support UI acceptance. All requests synthetic/intercepted; no real documents mutated. All browser processes terminal. Overall42 Verified/22 In progress. Backend authorization and final whole-candidate/release gates remain separate and open.
