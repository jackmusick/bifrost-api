# Shared contract reconciliation — 2026-09-08

This consolidates UI evidence across accepted routes. It does not replace final API/compiler, full-suite or exact-candidate delivery gates. Individual asset records are being reconciled separately against their actual consumers.

## Foundations and branding

Canonical tokens are vendored from design-system11da72e in bifrost-tokens.css and mapped through index.css. Fonts are locally hosted Inter, Prompt and JetBrains Mono. Control/surface/feature radii remain6/4/8px. Neutral canvas and paper retain distinct roles; semantic outcomes remain independent of tenant branding.

Current foundation-current.cjs15052 passes12 combinations: default, purple and near-white branding × light/dark ×320x480/1440x900. It asserts actual font availability and computed body/title families, exact canvas colors and radii, default teal/spectrum, matching activity/bridge aliases and tenant-derived gradients without default rainbow stops. Parent inspected default-dark320 and near-white-light1440. The current shell proof covers reduced-motion theme switching without View Transitions, navigation and portaled account/status controls.

| Consumer boundary | Accepted evidence |
| --- | --- |
| Shell/default/tenant themes | shell-review.md; foundation-current15052; brand-palette and branding unit tests in the full client run |
| Real action contrast and mobile interaction | Existing live-service design-foundations.admin.spec.ts run:5 tests including setup; measured light custom-brand action contrast in both themes and mobile form-palette interaction |
| Branding editor and live refresh | platform-settings-review.md: final branding73887 preserves drafts during upload-triggered read failure/retry; OrgScopeContext refresh no longer unmounts the route |
| Workflow execution/page/drawer | Current accepted execution-brand46167: four light/dark320/1440 custom-brand streaming, pause/latest and message-layout cases |
| Global editor | editor-acceptance.md: shell47126 exact custom-brand values, single editor and pane/focus lifetime; streaming82397 through terminal completion/result |
| Auth and account | Accepted auth route evidence plus account-settings-review.md; tenant branding, native virtual-authenticator creation and bounded MFA/recovery dialogs |
| Legacy inline apps | v1-compatibility.md: published/preview matrix4230; eight theme/width/custom-brand cases after utility-layer correction |

Palette tests include invalid/default input, blue/red/yellow/near-white/black and contrast checks. Branding tests cover owned aliases, replacement/reset and legacy override cleanup. These passed in the full2690-test run; its sole failure was the Events test clock, repaired separately.

## V1 and standalone ownership

The existing bifrost export registries retain their baseline names. Button native props/refs/asChild, CommandDialog auto-wrapper and CalendarPicker versus Calendar icon aliases have focused compatibility tests. The real legacy fixture exercises published/preview route recovery, controlled inputs, Select, tabs, Dialog, CommandDialog search and calendar bounds in both themes and widths.

Generated legacy utilities occupy bifrost-app-utilities below host components/utilities. Authored app CSS remains unlayered. Bundle schema4 refreshes old generated assets through the existing manifest path; it does not claim to sandbox arbitrary authored global CSS. Real compiler/bundler3651 passes18 tests and API quality25767 passes, as documented in app-editor-review.md. Current full client coverage also passes the compatibility/runtime tests. Final exact-candidate API/compiler gates remain due.

Standalone V2 retains its own full-document asset ownership. Accepted published/preview browser46375 covers eight theme/width custom-brand cases including failed import, bounded technical details and reload; related feedback/BundledAppShell/StandaloneV2 tests31937 pass28. Applications/runtime route evidence is consolidated in applications-review.md and PROGRESS.md. UI simulation does not claim a new backend publish execution or provider protocol.

## Shared composition

list-action-audit.md reconciles primary record entry and shared overflow for secondary actions, including integration mappings. Every affected list has narrow/wide interaction evidence in its route review. Shared overlays preserve focus trapping, dismissal and pending state through accepted consumers. Sonner/modal stacking is now resolved by shell-toast-current79220: immediate confirmation remains actionable while the preceding success notification exists. Parent inspected the short mobile result.

All14 family rows are reconciled at the UI-contract level. Remaining work is the per-asset evidence/retained-component reconciliation and final candidate validation/delivery, tracked in REVIEW-QUEUE.md.
