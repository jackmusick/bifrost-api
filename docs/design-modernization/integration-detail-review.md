# Integration Detail Review

Status: UI Verified. Application-wide release acceptance remains open.

This route is no longer a blank ledger entry. The current evidence set covers the integration header and mapping layout pass, the overview card layout and visible failed-mapping state, the provider/read/match/save/retry path, defaults/config editing, mapping config overrides, organization config save recovery, and the OAuth picker/callback flow. The remaining work is narrower than the old `coverage.md` row suggested.

Completed evidence already recorded in `PROGRESS.md` includes:

- `Integration header and organization mapping layout` and `Integration overview and visible mapping failures` for the responsive page shell, long value wrapping, 44px header actions, defaults dialog entry, OAuth menu entry, and visible mapping failure handling.
- `Integration manual entity refresh behavior`, `Integration auto-match controls and suggestions`, `Integration provider failure recovery`, `Integration mapping save feedback`, and `Integration partial-batch retry` for entity refresh, match suggestions, provider retry, retained failed batches, and failed-only retry.
- `Integration initial read recovery` and `Integration cached reads and family regression` for initial 500s, cached retention, and independent retries.
- `Integration configuration defaults dialog`, `Defaults zero/unset and integer validation`, and `Defaults JSON editor` for pending dismissal, inline save error retention, bool/int/JSON handling, and exact retry payloads.
- `Integration connection test panel` for the test dialog pending state, local error, retry, and wrapped result presentation.
- `Organization configuration save recovery`, `Shared integration configuration field presentation`, `Configuration override record layout`, `Override deletion recovery`, `Reusable override value editor`, and `Override JSON/boolean states and integration regression` for org-specific config editing, field controls, delete confirmation, and retry preservation.
- `Integration edit confirmations and missing-data guard`, `Integration editor provider lookup recovery`, `OAuth entity-ID picker`, `OAuth picker save recovery and standalone completion`, and `OAuth popup completion and callback message bounds` for edit confirmation sequencing, provider lookup retry, picker save/retry/Skip, and popup completion.

Final route acceptance:

- Current mapping lifecycle browser31014 passes four320/1440 light/dark custom-purple reduced-motion cases: failed authorization, refresh and disconnect with retry; disabled conflicting controls; expired reconnect; missing-mapping create failure/retry; popup completion/refetch. Parent inspected light320 expired state. Parent added disabled entity fieldset after initial46445 exposed an editable field during a request, and aligned expiry status with the overview. Sixteen component tests2657, scoped lint and full TypeScript94599 passed.
- Protected-route browser78325 passes all four theme/width cases for this route and Diagnostics: nonadmin denial, no attempted protected data reads, visible dashboard return. It uses an isolated synthetic browser session and proves UI gating, not backend authorization. Parent inspected dark320 denial. Router retains `ProtectedRoute requirePlatformAdmin`. Initial/cached read recovery and return navigation retain preceding evidence.
- The page is accepted using the accumulated route, shared-dialog, responsive-record, input validation, recovery, branding and keyboard evidence below. Final production candidate/build/full-suite gates remain application-wide work.

Current supplemental evidence:

- `integration-oauth-actions.cjs`12005 passed four320/1440 light/dark custom-purple reduced-motion cases: held token/authorize failure and retry, one popup per connect/reconnect, synthetic popup completion causing detail refetch, and one refresh-success toast. Parent inspected dark320. Removed duplicate page popup/success handlers; shared hooks retain ownership. No external provider flow or real mutation ran.
- `integration-config-short.cjs`92765 passed four320/1440x600 cases for eight-field defaults/org dialogs: fixed footer/error, pending guard, retained draft and successful retry. Parent inspected light320 org and dark320 defaults. Initial90625 caught missing flex constraints on the org form, corrected by parent. Terra reports14 existing tests and scoped lint passed; final parent org lint39127 passed.
- `integration-oauth-editor-route.cjs`30702 passed route-level create/edit pending/error/retry and request-contract checks, but screenshots exposed the disappearing header. Parent changed its layout to a fixed header/footer/error and independently scrolling form body; final8398 passed all four theme/width cases with title/error/footer visible;11 tests10354 and lint90006 passed. Final human-readable title has6 tests32283 and dark320 confirmation90545; parent inspected.

The delete branch is now covered by the current browser pass: `integration-delete-*` now passed four light/dark 320/1440 custom-purple reduced-motion cases for both mapping and OAuth dialogs, including pending, error, and retry states. Parent reviewed the light320 OAuth and dark1440 mapping captures.

The deletion change is limited to IntegrationDetail and the new reusable IntegrationDeleteDialog. Its focused test93283 and scoped lint/full TypeScript75104 passed. The other source changes summarized above belong to preceding migration batches.

The current overview pass renders structured defaults as JSON, wraps long keys, and gives expired tokens an Expired status/destructive icon even when the stored authorization status remains completed. Refresh/reconnect behavior is preserved. Final browser/test results are recorded in PROGRESS.md.

Relevant evidence paths:

- `docs/design-modernization/PROGRESS.md`
- `/tmp/bifrost-design-review/integration-read-check.cjs`
- `/tmp/bifrost-design-review/integration-cached-check.cjs`
- `/tmp/bifrost-design-review/integration-overview-check.cjs`
- `/tmp/bifrost-design-review/integration-match-check.cjs`
- `/tmp/bifrost-design-review/integration-provider-check.cjs`
- `/tmp/bifrost-design-review/integration-save-check.cjs`
- `/tmp/bifrost-design-review/integration-partial-check.cjs`
- `/tmp/bifrost-design-review/integration-defaults-check.cjs`
- `/tmp/bifrost-design-review/integration-values-check.cjs`
- `/tmp/bifrost-design-review/integration-json-check.cjs`
- `/tmp/bifrost-design-review/integration-test-check.cjs`
- `/tmp/bifrost-design-review/integration-confirm-check.cjs`
- `/tmp/bifrost-design-review/integration-edit-save-check.cjs`
- `/tmp/bifrost-design-review/integration-provider-read-check.cjs`
- `/tmp/bifrost-design-review/integration-delete-mapping-light-320.png`
- `/tmp/bifrost-design-review/integration-delete-oauth-light-320.png`
