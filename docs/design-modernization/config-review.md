# Config UI acceptance

Status: UI Verified for `/config`. Parent acceptance on2026-09-07. Global component, backend authorization and release acceptance remain separate.

## Composition and list behavior

The desktop table and mobile labeled cards preserve readable keys, type, value, organization and integration attribution. Long keys wrap; zero and false remain visible, and secret values are masked. Row identity opens editing and secondary actions live in the shared overflow menu. Mobile actions have44px targets. Search and selection operate independently: selections outside the filtered list remain selected for export.

Current custom-purple light/dark320/1440 browser12027 passes cards/table visibility, no horizontal overflow, zero/false/secret display, filtered select-all, preserved selection, exact-ID export/download, search clear and delete cancellation. Parent inspected dark320. Browser74436 passes initial/cached GET500/retry without dropping records or selection. Final browser10230 passes organization/global/all server-query selection in all four theme/width cases. Initial1242 matched option names without their secondary descriptions; corrected the fixture before acceptance.

## Create and edit

ConfigDialog uses a bounded scroll region with fixed footer actions. Pending mutations disable fields/actions and block dismissal. A synchronous submission guard prevents duplicate saves; the form helper runs inside the event handler. Save failures focus a semantic inline error and preserve values for retry. Lint rejected the initial render-time helper invocation; the final source passes lint/TypeScript36077 and three ConfigDialog tests16358.

Browser46748 passes four custom-brand theme/width JSON edit cases: held failure, pending protection, focused error, retained JSON and equal-payload retry. Parent inspected dark320. Browser67581 passes all four cases across string/integer/boolean/JSON/secret creation, initial required-field validation, selected organization payload, POST500 retry and identical retried data. Zero and false remain intact. Existing secrets open blank in a password input; unchanged secrets are omitted from PUT and entered replacements are included. Parent inspected light320 creation error and dark320 secret edit. No real secrets were accessed; these are synthetic values.

## Delete and import

Reusable ConfigDeleteDialog replaces automatic-closing inline confirmation. It guards duplicate requests and pending dismissal, focuses inline server errors, retains the key for retry and restores focus to Add configuration. Long keys wrap, controls have44px targets and the dialog is bounded90dvh. Dependency copy explains that workflow consumers may fail, without an obsolete repository-path instruction. The delete hook's optional error-toast suppression preserves other callers' defaults.

Browser26353 passes four custom-purple light/dark320/1440 held DELETE500/retry/focus cases; parent inspected dark320. Six Config page tests56913 pass including retained-delete retry; source TypeScript61112 passes. Intermediate old-mock failure was corrected to mutateAsync.

Import browser98809 passes malformed JSON, selected valid config, POST500 and retry to completion in all four theme/width cases; parent inspected dark320. It uses the shared ImportDialog, whose independent component inventory remains separate. Browser logs use the original integration fixture wording, but endpoint and entity data target configs. No real imports occurred.

## Access, evidence and limits

App.tsx guards `/config` with requirePlatformAdmin. Browser7792 passes four synthetic non-admin denied cases without Config data requests; the existing shared denied-page visual contract is unchanged. These are frontend permission checks, not backend authorization proof.

Evidence scripts/screenshots live in `/tmp/bifrost-design-review/`; rejected intermediate candidates and process outcomes are in PROGRESS.md. All browser mutations were intercepted. Release-wide tests/build, remaining routes/components, V1 compatibility and final artifact delivery remain open.
