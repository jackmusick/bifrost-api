# Audit route acceptance reconciliation

Parent UI review accepted `/audit` on 2026-09-07. This note consolidates source, tests and rendered evidence; application-wide release acceptance remains open.

Route surface:

- `/audit`

Current source shape:

- `client/src/pages/audit/AuditLogPage.tsx`
- `client/src/pages/audit/AuditFilters.tsx`
- `client/src/pages/audit/AuditPagination.tsx`
- `client/src/pages/audit/AuditEventCards.tsx`
- `client/src/pages/audit/AuditOutcome.tsx`
- `client/src/pages/audit/AuditLogPage.test.tsx`
- `client/src/hooks/useAuditLog.ts`
- `client/src/components/ProtectedRoute.tsx` via the `audit` route in `client/src/App.tsx`

## Source requirements and evidence

| Requirement | Evidence | Status |
| --- | --- | --- |
| Platform-admin-only route protection | `ProtectedRoute` requires `requirePlatformAdmin`; unit coverage plus final frontend role-fixture matrix66739 verifies nested route denial, zero audit fetches and keyboard dashboard return | `current-run-automated-pass` + `current-run-browser-pass` |
| Desktop table and mobile card layouts | `AuditLogPage.tsx` branches on `useMediaQuery("(min-width: 1024px)")`; `AuditLogPage.test.tsx` exercises long-value rows in the fixture; `/tmp/bifrost-design-review/audit-route-acceptance.cjs` captured 320 and 1440 in both themes | `current-run-browser-pass` |
| Search, action, outcome, and date filters | `AuditFilters.tsx` preserves query format; `AuditLogPage.tsx` converts filters to `useAuditLog` params; unit test covers action/search wiring and the browser script exercises action/outcome/search/date filters plus clear-reset | `current-run-automated-pass` + `current-run-browser-pass` |
| Date validation and blocked invalid range requests | `AuditFilters.tsx` sets the date-range error and ARIA wiring; `AuditLogPage.tsx` disables fetches while the range is invalid; the browser script verifies the invalid state and that the invalid range does not issue a request | `current-run-browser-pass` |
| Pagination and keyboard activation | `AuditPagination.tsx` keeps 44px controls, previous/next state, and the page counter; the browser script exercises Enter and Space activation on Next/Previous | `current-run-browser-pass` |
| Initial and cached read recovery | `AuditLogPage.tsx` distinguishes initial load failure vs refresh failure and keeps loaded rows visible on refresh errors; the browser script forces both failure modes and verifies retry recovery | `current-run-browser-pass` |
| Long resource/context readability | `AuditLogPage.tsx` now wraps full resource IDs and context text on desktop instead of truncating or slicing them; the browser captures show the long identifiers fully visible at 1440 and still readable at 320 | `current-run-browser-pass` |
| Semantic brand application | `client/src/lib/branding.ts` and `client/src/lib/brand-palette.ts` apply the brand token; the browser script asserts the derived token values exactly after load (`#7c3aed` light, `#9c6af1` dark) | `current-run-browser-pass` |
| Reduced motion | The spinner uses `motion-reduce:animate-none`; supplemental held-loading checks assert computed animationName is `none` | `current-run-browser-pass` |

## Browser evidence

Current-run rendered proof:

- `/tmp/bifrost-design-review/audit-initial-error-light-320.png`
- `/tmp/bifrost-design-review/audit-loaded-light-320.png`
- `/tmp/bifrost-design-review/audit-filtered-light-320.png`
- `/tmp/bifrost-design-review/audit-date-invalid-light-320.png`
- `/tmp/bifrost-design-review/audit-cached-error-light-320.png`
- `/tmp/bifrost-design-review/audit-final-light-320.png`
- `/tmp/bifrost-design-review/audit-initial-error-light-1440.png`
- `/tmp/bifrost-design-review/audit-loaded-light-1440.png`
- `/tmp/bifrost-design-review/audit-filtered-light-1440.png`
- `/tmp/bifrost-design-review/audit-date-invalid-light-1440.png`
- `/tmp/bifrost-design-review/audit-cached-error-light-1440.png`
- `/tmp/bifrost-design-review/audit-final-light-1440.png`
- `/tmp/bifrost-design-review/audit-initial-error-dark-320.png`
- `/tmp/bifrost-design-review/audit-loaded-dark-320.png`
- `/tmp/bifrost-design-review/audit-filtered-dark-320.png`
- `/tmp/bifrost-design-review/audit-date-invalid-dark-320.png`
- `/tmp/bifrost-design-review/audit-cached-error-dark-320.png`
- `/tmp/bifrost-design-review/audit-final-dark-320.png`
- `/tmp/bifrost-design-review/audit-initial-error-dark-1440.png`
- `/tmp/bifrost-design-review/audit-loaded-dark-1440.png`
- `/tmp/bifrost-design-review/audit-filtered-dark-1440.png`
- `/tmp/bifrost-design-review/audit-date-invalid-dark-1440.png`
- `/tmp/bifrost-design-review/audit-cached-error-dark-1440.png`
- `/tmp/bifrost-design-review/audit-final-dark-1440.png`

The verification script:

- `/tmp/bifrost-design-review/audit-route-acceptance.cjs`

## What is covered and what is not

Covered:

- admin route shell
- desktop table view
- mobile card view
- long row content readability
- filter state transitions and reset
- invalid date range handling
- retryable initial and cached read failures
- keyboard activation for pagination
- brand token application

Covered by synthetic frontend boundary evidence:

- non-admin access message and keyboard dashboard action; authenticated transport remains unchanged, so this is not a server authorization test

Not claimed here:

- deployment signoff
- any broader product-level checklist beyond the route

## Test evidence

- `./test.sh client unit src/pages/audit/AuditLogPage.test.tsx`
- `npx eslint src/pages/audit/AuditLogPage.tsx src/pages/audit/AuditFilters.tsx src/pages/audit/AuditPagination.tsx src/pages/audit/AuditEventCards.tsx src/pages/audit/AuditOutcome.tsx src/pages/audit/AuditLogPage.test.tsx`
- `node --check /tmp/bifrost-design-review/audit-route-acceptance.cjs`
- `node /tmp/bifrost-design-review/audit-route-acceptance.cjs`

## Parent acceptance

Parent inspected desktop full resource/context wrapping, mobile filtered records, and initial/cached errors after the worker correction. Supplemental loading/empty/filter-reset/invalid-query checks completed for light320/1440 in22665, dark320 in55449 and dark1440 in68105. Each asserted the held loading spinner animation is `none` with reduced motion, no pagination for empty data, filter reset, no request with an invalid date range, and document bounds. The empty state now distinguishes an empty log from no matching results. Parent inspected light/dark empty-state captures.

The initial synthetic-token permission fixture produced authentication/navigation races; some DOM-passing captures were blank and parent rejected them. Final `audit-denied-render-check.cjs`66739 injects frontend organization-member role flags into the development AuthContext module while preserving the authenticated transport. It proves the actual nested route boundary and rendered member shell, zero Audit fetches, visible keyboard Return to Dashboard, and bounds at320/1440 in light/dark. Parent inspected final dark320 and light1440 captures (`audit-denied-stable-*`). This is frontend permission presentation proof, not a backend authorization test.

Review found NoAccess unnecessarily imposed100dvh inside the app shell and described a page restriction as loss of system access. Added backward-compatible optional embedded/message props; platform-admin ProtectedRoute uses the compact in-page presentation and specific access requirement. The default full-screen system-denial presentation remains available. Eight NoAccess/ProtectedRoute/Audit tests60733 and scoped ESLint83698 passed.

UI route status is Verified. Final application-wide shared-component review, exact-HEAD tests/build/pre-PR, and delivery remain open.
