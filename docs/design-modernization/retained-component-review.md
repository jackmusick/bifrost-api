# Retained component review

These components have no detected render path from the current router, main entry point or public runtime registries. They remain exported in their existing files. Their review scope is the component interface and isolated rendering; an absent consumer is not a reason to add a route, invent a provider integration or delete an API during this migration.

The ownership map was checked against static imports, lazy page bindings and runtime exports. Related imports between retained files do not make that subtree a live page. Existing source and isolated evidence below were reconciled by the parent; full client coverage passed453 files /2690 tests before the final retained fixes.

| Retained files | UI evidence and disposition |
| --- | --- |
| ExecuteForms | Parent found false emptiness after a failed read and narrow grid overflow. Read-error component now supports initial/cached retry, long values wrap, invalid-form visibility/locks and execution navigation are preserved. Browser22253 passes four light/dark320x480/1440x900 cases with a260px narrow content container. Parent inspected dark320 populated and light320 long-error states. Three focused tests cover retry/filtering/navigation. No route added. |
| QueueSection | diagnostic-parts96716: six light/dark320/768/1440 isolated queue/execution parts, full identifiers, duration formatting, loading and refresh callback. Existing ExecutionRowData type consumers remain intact. |
| GenerationModelSettings | model-parts6502: six isolated theme/width cases, catalog/manual input modes, modality callbacks and unique IDs. Controlled setters retained. |
| ModelCapabilityEditor | Visual layout/callback evidence from model-parts6502 applies. Parent found stale detection/verification responses could replace newer props or manual choices; parent-reviewed request-lifetime repair now guards committed input identity, StrictMode/unmount, manual edits before/during lookup and duplicate requests. Ten current tests pass, preserving original success/payload/control coverage. This asset is UI Verified. |
| verdict-toggle | verdict96468: six theme/width keyboard/click up/null/down callbacks, pressed/disabled state, narrow44px targets and reduced-motion feedback. Six tests passed. |
| Chip, KVList, MetaLine | Final54982: four theme/width long-label/identifier, zero/missing metadata and bounds cases; semantic tokens, complete values and responsive description layout. Nine tests passed. |
| FleetStats | fleet-parent-check: four theme/width cases with bounded statistics and keyboard review callback; props and optional chart series retained. |
| NeedsReviewCard | agent-narrative85041: four theme/width narrative/review activation and long-content cases. Active agent routes use separate accepted components. |
| AppUpdateIndicator, NewVersionBanner | compact-status91905: four theme/width cases with long attribution, status wrapping and refresh callback. Existing visibility restrictions remain covered by tests. |
| ChangesList | Final6745: four isolated theme/width full paths,44px rows, keyboard callback, collapse/reopen, loading and empty states. |
| ConflictResolutionBanner | conflict-banner47581: six theme/width full-path, bounds and all three keyboard resolution callbacks. No active conflict flow inferred from this isolated surface. |
| FileTree, FileTreeNode, FileTreeContextMenu | Preflight28758 plus node66883: bounded diagnostics and focus return, deeply indented long paths, rename/create inputs, folder/file/context callbacks and keyboard dismissal. Parent's current retained-controls59889 also verifies Delete uses the canonical destructive menu variant and activates the same callback. Live editor uses components/file-tree, covered separately. |
| FieldsPanel, FormInfoPanel | fields-panel85730 and form-info35878: controlled reorder/delete cancellation/confirmation, live order announcement, full values, scope/field setters and no accidental parent-form submission. Six/seven focused tests passed. Live designer uses its accepted DnD panels. |
| OAuthConnectionCard, RefreshJobStatus | oauth-card22846 and refresh-status9946: four theme/width copy failure/retry, pending/lifetime protection, initial read recovery, retained refresh data, safe timestamps and log-dialog focus. Existing provider transport remains unchanged. |
| CronTester | cron73665: four theme/width validation error/retry, next runs, copy recovery, cleared input, StrictMode and stale-response protection. |
| DocumentQueryPanel | Current44598 isolated query matrix: condition add/apply/remove/clear, boolean default, accessible labels, responsive alignment;23 related tests passed. |
| UserDetailsDialog, UserRolesDialog | user-dialogs25680/43960/49669 and user-roles58078: bounded long-user/role/form states, read retry and assignment recovery. Public close, superuser restriction and role mutation interfaces retained; current focused tests passed in the full client suite. The routed user detail uses separately accepted controls. |

The retained slider is public through bifrost-runtime rather than unmatched. Parent expanded its interactive rail to44px without changing thumb appearance or props. Current retained-controls59889 passes four theme/width real pointer clicks above the track, keyboard adjustment and disabled-value preservation; parent inspected dark320. That same run covers the retained file-tree destructive action. Initial56093 measured Radix's inner thumb wrapper instead of the rail and is superseded by59889.

No real accounts, workflow executions or provider mutations were performed by these fixtures. Final thirteen ModelCapabilityEditor/ExecuteForms tests20312 pass. Scoped lint passes; exact-candidate validation remains required.
