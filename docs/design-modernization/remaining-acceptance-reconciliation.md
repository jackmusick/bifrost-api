# Remaining acceptance reconciliation

Current as of 2026-09-10. The ledger is **56 targeted browser journeys passed** after Dashboard, SECURITY-02 recovery login, SECURITY-03 password change, non-user role assignment, and form builder rebind/reorder/delete-field persistence passed. Form deactivation and the retained Disabled card also passed after reload.

This reconciliation does not claim every supported click is covered. It records which primary route families now have adequate browser proof and where remaining work is finite or intentionally lower-layer.

## Closed or adequate for this acceptance phase

- Home: collection CRUD, catalog browse, pinning, filters, ownership/member visibility, and app/form/agent launch.
- Dashboard: API-backed metric cards, execution summary, refresh, and Workflows drilldown.
- Workflows/global editor: workflow list/detail/settings/execute entry plus global editor exact file edit/save/switch/reload persistence.
- History/executions: history display, details, logs/result/input tabs, realtime completion, cancel, schedule, and picker geometry.
- Forms: browse/open, metadata save/reopen, field add/reorder/delete persistence, launch-workflow/default rebind, member submit/result, role denial, public/embed/HMAC flows, solution runtime, and Home launch.
- Apps: editor persistence, replace, publish notification, preview/live navigation, V1 runtime compatibility, and solution runtime resource resolution.
- Agents: fleet browse/filter, private create/reopen, detail chat handoff, real agent execution plus verdict-created flagged run review, disabled tuning state, mixed setup real Apply persistence, and backend apply/verdict proof.
- Chat: persisted user/assistant messages with local model fixture and reload; attachment/artifact UI remains mixed where provider/library behavior is synthetic.
- Admin/data: config lifecycle, table/shared data-table behavior, files share/upload/preview, knowledge/memory coverage, organizations, users invite/bulk org, roles lifecycle/user/non-user assignment, solutions lifecycle/export/runtime, diagnostics/audit/report evidence.
- Resources: integration card/mapping persistence, generic webhook/event/subscription delivery, review-pack mapping-to-workflow execution, MCP management/settings/personal/catalog, entity management evidence from current inventories.
- Settings/account/shell: AI chat instructions, AI pricing, MCP/GitHub/SSO/workflow-key/artifact/branding settings, Maintenance component actions, account profile/security/password, menu/HomeBrowse/global editor/shared navigation passes.

## Required before closure

1. All tracked journeys must pass together on the candidate, not only in targeted iterations.
2. Push after ownership checks are satisfied.
3. Clean pre-PR/current-main run from the parent stack.
4. Nightly run on the agreed environment.
5. Parent visual review of the redesigned flows and screenshots.

## Explicitly outside the local acceptance denominator unless separately promoted

- Real third-party OAuth/provider callbacks and provider-side subscriptions.
- Secure credential runner behavior and persistent secret-backed provider install.
- External model quality or non-deterministic proposal generation.
- External assistant/plugin installation beyond deterministic download/link checks.
- Exhaustive every-filter/every-sort/every-validation/every-error permutation coverage where component/backend tests already cover the contract.
- Browser-harness-sensitive copy/download/passkey variants unless a deterministic fixture is available.
