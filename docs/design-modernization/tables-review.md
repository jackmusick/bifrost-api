# Tables UI review

Status: UI Verified for /tables and /tables/:tableId. Final release gates remain open.

## Tables editor verification (2026-09-07)

Previous goal turn was progress: Config accepted. TableDialog now uses a synchronous submission guard plus focused/scrolled root save-error alert without a default outline. Guard starts after schema validation so invalid JSON cannot lock the form. Existing policy validation, solution-managed protection, pending Monaco/template/field locks and scope immutability remain. Form helper is invoked in submit handler to satisfy ref-use lint.

Twelve TableDialog tests63824 and source lint/full TypeScript57376 pass. Initial browser27779 passed create then failed obsolete standalone Edit button. Intermediate47127 used wrong menu label; corrected to `${table.name} actions`. Final18512 passes eight custom-purple light/dark320/1440 create/edit cases: both Monaco editors rendered, description draft, pending field/template/Cancel locks, Escape protection, focused server error, visible footer and same-payload retry. Parent inspected light320 Edit error. All writes intercepted; no real tables changed. All handles terminal; diff check passes.

Coverage38 Verified/26 In progress. Tables list/detail remain open. Next source gap: Tables.tsx still uses automatic-closing AlertDialogAction for delete; preserve existing is_solution_managed defense and add pending/error/return-focus recovery. Then current list/recovery/import/export, managed table restrictions, TableDetail documents/query/policy/claims and remaining route acceptance. Existing fixtures: tables-mobile-check.cjs, tables-recovery-check.cjs, table-detail-{check,states,interactions}.cjs; adapt current overflow names and0-38 preview. Goal active, no blocker.

## Tables delete and list verification (2026-09-07)

Previous goal turn was progress: editor recovery verified. New page-local TableDeleteDialog replaces automatic-closing delete confirmation. It has synchronous duplicate guard, pending Cancel/Escape protection, focused inline server errors, same-record retry, long-name wrapping,44px controls and Create table focus fallback. Existing solution-managed menu and confirm defenses remain. Four Tables tests76055 pass including new failed-delete retry. Initial source lint/TypeScript63205 and final scoped lint97728 pass; final full TypeScript28487 is running at this entry.

Initial browser86353 did not find the row after the saved preview login expired. Refreshed83295; final delete45256 passes all four custom-purple light/dark320/1440 held500/pending/error/retry/focus cases. Parent inspected dark320. Final list25759 passes four custom-brand cases: mobile cards/desktop table, long names/no overflow, search/selection preserved, filtered select-all, managed Edit/Delete disabled and keyboard overflow/delete-cancel. No real tables deleted; all mutations intercepted. Browser log inherited generic disable/delete wording but actual endpoint is /api/tables/:id DELETE.

Inventory now133 page modules (includes new page-local component),360 feature components,53 primitives,64 routes; coverage38/26 unchanged. Tables routes remain In progress: list read recovery/import/export request proof, detail documents/query/policy/claims and acceptance audit remain. TableDetail already uses page-local DocumentDeleteDialog; inspect before duplicating work. Goal active, no blocker.

Final full TypeScript28487 passes. Parent inspected dark320 list. All parent handles terminal; diff check passes.

## Tables read recovery and document interactions (2026-09-07)

Previous goal turn was progress. List recovery27235 passes four custom-purple light/dark320/1440 initial/cached GET500/retry cases retaining selection and search. DocumentDeleteDialog now focuses/scolls its inline error, bounds height90dvh, explicitly guards Escape and restores focus to the stable Filters control through useDialogReturnFocus. Existing synchronous guard/retry remains.

Initial detail8174 and final3648 each pass six custom-purple light/dark320/768/1440 cases: page-local search, server pagination with preserved search, filter drafting/apply/reopen, JSON disclosure, pending DELETE500 recovery/retry, retained documents on query failure and retry. Final includes explicit return-focus assertion. Parent inspected dark320 composition; clean record capture8237 running because the initial final screenshot still showed the preceding success toast. Six TableDetail tests41616 passed before return-focus wiring; final34199 running. Initial lint/full TypeScript62194 passes; final36109 running. All mutations synthetic intercepted; no real documents deleted.

Coverage38 Verified/26 In progress. Remaining Tables acceptance: document editor/create/update/schema/claims; list import/export request proof; table detail missing/loading/permission states; final matrices. No blocker, goal active.

Final six TableDetail tests34199 and full TypeScript36109 pass. Clean dark320 record capture8237 passes; parent inspected the record card and JSON disclosure. All parent handles terminal; diff check passes.

## Document and Custom Claims recovery (2026-09-07)

DocumentDialog now focuses/scolls save errors and explicitly protects Escape while pending. Nine tests95578 and source lint/full TypeScript33966 pass. Real Monaco document create/edit93530 passes eight custom-purple light/dark320/1440 cases: invalid object drafts, short-screen footer, pending locks, retained JSON and exact POST/PATCH retry payloads. Parent inspected dark320 edit error. Table detail states51762 is no longer available to poll after context recovery; its saved log has all four completed cases for loading,500/403/404, solution back link, document read failure/retry and branded empty state. Parent inspected dark320 empty screenshot; do not infer an unavailable exit status.

Custom Claims now uses page-local ClaimDeleteDialog with synchronous guard, pending Cancel/Escape lock, focused inline errors, retry and stable Add Claim focus restoration. CustomClaimEditor now has synchronous save protection and focused error recovery. Nine combined tests18976 pass; an added failed-save/retained-payload regression brings editor tests to five57457. Source lint/full TypeScript97522 pass. Delete browser4277 passes four light/dark320/1440 menu/edit-cancel/delete-failure/retry/focus cases. Read recovery81459 passes four loading/initial/cached failures with retained search. Parent inspected dark320 delete error.

First claim-save fixture55673 used PUT despite service PATCH and failed its request-count assertion; corrected fixture68440 passes four real-Monaco edit/pending/error/draft/exact-payload retry cases. Initial unexpected PATCH targeted only the synthetic claim name; subsequent fixture mutations intercepted. Parent screenshot review caught Save below the viewport when focusing the error. Added scroll margin below the alert; final browser6807 checks Save remains in viewport and is running at this entry.

Coverage remains38 Verified/26 In progress; inventory134 page modules,360 feature components,53 primitives. Table routes remain open for final acceptance, imports/exports, claims create/scope/managed behavior and document dialog return-focus proof. No blocker. Goal remains active.

Final browser6807 passes all four claim-save cases with Save explicitly in viewport after failure. Parent inspected corrected dark320 screenshot. All parent handles terminal; diff check passes.

## Tables route acceptance (2026-09-07)

Previous goal turn made progress. DocumentDialog now accepts the stable Filters return-focus ref and applies the shared dialog focus lifecycle. Initial browser2760 failed its focus assertion but its screenshot handler masked the error after context close; corrected handler and focus wiring. Final14577 passes all8 create/edit light/dark320x600/1440x900 validation/pending/failure/retry/focus cases. Fifteen document/detail tests80295 and scoped lint/full TypeScript14967 pass.

Export68430 passed four selected-ID/all-ID download cases, then the import fixture failed an incorrect “Tables” heading (actual Data Tables). Corrected import68755 passes four custom-purple light/dark320/1440 malformed-file/server-error/retry cases; same terminal batch passes four claim scope race cases and four real-Monaco create/held-error/exact-payload-retry cases. Managed claims have no editable action menu. Parent inspected dark320 import and claim-create error screenshots. Fresh synthetic non-admin contexts33326 pass both routes in all four theme/width combinations with zero table data reads. Final detail loading/unavailable/empty/branding rerun9793 passes all4 cases and has confirmed exit0.

Both /tables and /tables/:tableId are now UI Verified based on this evidence and preceding record/menu/editor/query/policy matrices. Coverage40 Verified/24 In progress. Backend behavior/authorization and final whole-candidate tests/build/release remain independent gates. All parent processes terminal, no blocker. Remaining routes include files/editors, applications/runner, solutions, agents, knowledge, entity management, settings/reports/user settings, chat and dashboard/index.
