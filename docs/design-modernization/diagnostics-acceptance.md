# Diagnostics UI acceptance

Status: UI Verified. Application-wide release gates remain separate.

The route uses the shared page header and tabs. Workers, scheduler replicas, scheduled tasks and platform jobs use readable mobile records, with comparison tables at wider container sizes. Long identifiers remain available; row/drawer actions support keyboard use. Status colors are semantic and primary actions follow the custom brand.

Recorded evidence in PROGRESS.md and the existing browser logs:

- Worker/process disclosures and recycle pending/failure/retry: six light/dark320/768/1440 cases in `diagnostics-workers-check.cjs`. Queue loading failure/retry, full identifiers, server total and keyboard popover/focus return: four cases in `diagnostics-queue-check.cjs`.
- Scheduler replica/task layout and recent-run keyboard activation: six cases. Run history failure/retry, logs and switching: six cases in `scheduler-drawer-browser.log`.
- Platform jobs pagination, keyboard detail entry and wrapping: six cases. Cancellation remains open while pending/on failure and retries successfully: six cases. Initial/cached read failures retain records and recover: six cases in `platform-job-recovery-browser.log`.
- Scheduler initial/cached read recovery80621: four cases. Memory chart error/retry/range and custom-brand colors49672/50729: four cases, with parent-reviewed chart/error/axis captures.
- Current nonadmin route boundary78325: four320/1440 light/dark custom-brand cases, no protected reads, visible dashboard return. Parent inspected mobile denial. This uses a synthetic browser identity and proves frontend gating only.

The current final matrix combines custom branding, actual route composition, queue, app-socket disconnect/reconnect, platform-job and run-drawer clipboard failure/retry. Parent reviewed dark320 job and light1440 run drawer captures without toast obstruction. The light320 case passed3362; the remaining light1440/dark320/dark1440 cases passed88403, completing the four-case matrix. Earlier authored-script existence was not accepted as execution evidence. Vite socket interception and desktop row selectors were corrected before successful cases.

The corrected disconnect check exposed a real defect: `useWorkerWebSocket` only set connection status at initial connection. It now subscribes to status changes and removes that listener on cleanup. Regression90775 passes; scoped lint37174 and full TypeScript94599 pass. This does not change worker commands or socket protocol.

All mutation/provider responses in these fixtures are intercepted. Prior built-artifact smoke19881 additionally covered loaded Diagnostics with a real live worker connection, but its build5692 predates later migration changes. Final production build, full suite and exact-HEAD release checks remain due.
