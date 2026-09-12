# Form runtime acceptance

Status: UI Verified. Routes: `/execute/:formId`, `/embedded/forms/public/:publicKey`, `/embedded/forms/hmac/:formId`.

## Current rendered evidence

- Runtime read recovery70509: custom-purple light/dark320/1440x600; initial failure/retry and cached failure preserve entered answers.
- Runtime submission16374: same four cases; pending input protection, focused inline failure, visible Submit retry action, preserved answers and on-page confirmation. Thirteen FormRenderer tests59991 cover submission behavior including duplicate-submit suppression.
- Scheduling60967: same four cases; relative-time selection, calendar/time popover bounds, failed submission retains delay, retry sends3600seconds and reaches History. Scheduled runs no longer announce that execution has started. Parent inspected light320 picker.
- Public embed79529: same four cases; long labels/help text, default-to-hidden header presentation, transparent canvas, no scheduling controls, touch controls, on-page confirmation. Parent inspected dark320 form.
- HMAC76908: same four cases reach the actual ExecutionDetails component after submission. Parent rejected missing run identity/status in the embedded result. Added a compact header using existing RunDetailHeading/RunStatusBadge without workspace actions. Final heading checks91687 pass all four cases;10 ExecutionDetails tests42430 pass. Embedded forms also suppress the redundant execution-ID toast; final browser5553 passes all four cases; parent inspected corrected dark320. Final scoped lint/full TypeScript4666 and13 FormRenderer tests40784 pass.
- 36 tests34067 across RunForm, FormCaptcha, FormConfirmation, ScheduleControls and DateTimePicker pass.

- Startup recovery52563: all four custom-purple theme/width cases show the server failure reason, prevent incomplete submission, expose Retry form data, show pending feedback, then recover the form. Parent reviewed dark320 failure and light320 loading. Three useLaunchWorkflow tests13615 cover retry, stale response isolation and moving to a form without startup;13 FormRenderer tests59454 also passed. Hook uses shared API error parsing. Final source checks are recorded in PROGRESS.md.

- Dynamic choice recovery21591: four custom-purple light/dark320/1440x600 cases prove HTTP failure, explicit retry, protected pending action, retained answers and recovered selection. Parent reviewed dark320 pending panel.22 service/renderer tests39731 pass, including failed-vs-empty response distinction and blur-triggered reload with stable recovery feedback. Final source checks recorded in PROGRESS.md.

- Dependent-field review73161: four custom-purple light/dark320/1440x600 cases exercise out-of-order responses, current autofill, conditional visibility, reset of selected child on parent change and invalidation after clearing the parent. Parent reviewed dark320 populated form.16 FormRenderer tests68236 pass, including late obsolete success/failure and retained current autofill. Requests with identical in-flight inputs are shared, and only the current request may update options/error/autofill. Final source checks recorded in PROGRESS.md.

- Startup expression dependencies49889: all four theme/width cases load choices automatically after startup recovery, with correct expression inputs, a single option request, autofill and conditional field visibility. Parent inspected dark320. Providers now reload from context changes and independent requests run concurrently;17 tests71355 pass. Final dependent-field regression83273 also passes all four cases after this change.

- Real iframe35117 and final fragment-entry41770: four custom-purple light/dark320/1440x600 cases render the form inside an iframe, consume/remove a synthetic fragment token, submit to confirmation, focus confirmation and send origin/form-scoped submission and positive-height resize messages to the parent. Parent inspected dark320 confirmation. This proves browser delivery/composition, not server signature verification.
- Embedded live execution34533: four theme/width cases consume actual WebSocket protocol messages, show a long mobile log with more than180px message width, then transition to Failed with readable reason and retained logs. Parent inspected light320 running and failed screenshots. Requests/stream events are synthetic; no workflow executed.

- Backend entry89711:20 actual isolated-stack e2e tests pass for HMAC redirects/signatures, verified startup context/handle binding, own-form execution and cross-form access restrictions, publication lifecycle, public fragment/presentation redirects, exact-form confirmation/revocation, upload ownership and publication validation. These tests exercise the server contract separately from rendered browser fixtures.

## Verification limits and release scope

Browser mutations and execution reads were intercepted; no workflow was executed. Public/HMAC fixtures use synthetic routing claims and navigate from the real app document to the embedded client route. This proves client composition; final41770 adds actual iframe fragment delivery. Backend public-key/HMAC entry and signature checks passed in89711. Browser CAPTCHA challenge interaction remains covered through local component fixtures, not a live external challenge. An earlier document-fulfillment fixture failed browser private-network resource checks; it is not acceptance evidence.

These three routes have completed UI acceptance using the consolidated evidence above. Wider shared schema/V1 compatibility, final production-candidate validation and application-wide release gates remain open. Backend tests execute synthetic workflows only in the isolated test stack; the browser fixtures do not execute workflows or change customer records.
