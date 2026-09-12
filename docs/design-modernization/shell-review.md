# Shared layout review — 2026-09-08

The regular Layout and padding-free ContentLayout share PageShell, Header and Sidebar. Canonical design contract: DESIGN.md and the design-system repository at 11da72e. Regular content uses 16/24/32px responsive padding; chat and execution retain ownership of their inner layout and scrolling. Embedded content remains free of workspace chrome.

## Header and navigation

The normal mobile header now fits its primary controls on one row. Temporary update, collaboration and passkey indicators get a separate row below 1280px. All primary controls remain directly accessible, including the optional AI connection menu. Long account names truncate on desktop and yield to the avatar on smaller widths. HeaderStatusIndicators centralizes the conditional status group without mounting duplicate subscriptions.

Synthetic browser shell-current.cjs passes six light/dark cases at 320x480, 768x900 and 1440x900: 44px controls, single-row default header, narrow navigation sheet and desktop inverse, keyboard dismissal/opener focus, account menu, regular-layout padding and content bounds. Reduced-motion theme switching changes the theme without invoking the View Transitions API. Parent inspected mobile navigation/account/content captures. Prior shared-shell proof 45797 covers regular workflow and full-width chat routes with sidebar persistence.

shell-run-current.cjs passes six cases for the AI connection menu: clipboard failure remains inline, HTTP fallback retries copy the exact MCP URL/setup prompt, Escape restores opener focus. The menu uses the shared clipboard helper and synchronous pending protection. Parent inspected the final single-row mobile header.

shell-status-current.cjs passes six crowded-header cases with an update available, another developer watching files, passkey setup and AI connection enabled. Every visible header button has a 44px target, fits the viewport and does not overlap another button. The file activity popover dismisses to its opener. Parent inspected light320, dark768 and light1440 screenshots. The tablet capture exposed split artifact filter options; the filter group now stays together and search wraps as a unit. Final six-case run54823 passes and the corrected dark768 composition was inspected.

## Overlay stacking

Sonner notifications use z-index45, above the header but below modal layers. shell-toast-current.cjs (79220) passes four light/dark320x480/1440x900 cases: rename succeeds, a delete confirmation opens immediately while its success toast is still present, Cancel is the actual hit target and clicking it closes the dialog and returns focus without a deletion. Parent inspected light320 with the notification behind the modal. This resolves the shared stacking issue recorded in chat-review.md.

## Automated verification

- ./test.sh client unit src/components/layout/PageShell.test.tsx src/components/layout/Sidebar.test.tsx src/components/layout/AccountMenuContent.test.tsx src/components/layout/BifrostRunMenu.test.tsx src/contexts/ThemeContext.test.tsx — 16 tests across five files pass (13475).
- Scoped ESLint for Header, HeaderStatusIndicators, BifrostRunMenu and its tests, ThemeToggle, Toaster and ArtifactsLibrary passes; full npm run tsc passes (70653).
- PageShell tests preserve loading, denied access, organization access and bare embedded content. Sidebar and account tests preserve route/logout contracts. Browser fixtures intercept APIs and use synthetic identities; no live account or data writes.

The additional 1024/1280px check caught a real overflow at 1024px with every status enabled. The compact treatment now extends through 1279px, and account text appears at 1280px. Final browser88894 passes all four breakpoint/theme cases; parent inspected dark1024 and light1280. Both layout route rows are now UI Verified, bringing the route total to64/64. Global shared-family reconciliation, compatibility/branding, full suites/build and exact-candidate delivery checks remain separate.
