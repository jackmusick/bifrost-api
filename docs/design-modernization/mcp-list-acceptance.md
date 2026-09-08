# MCP servers list acceptance

Status: UI Verified. Scope: `/mcp-servers`, including server creation and OAuth discovery. Server details and connection editing have separate acceptance work.

The list uses native record links, desktop rows and mobile cards. Search, loading, empty results, failed reads and unavailable connection counts remain explicit. New-server creation uses a scrolling form body with fixed header/error/actions. OAuth fields have associated labels and the shared 44px selector; failed discovery retains inline manual-entry guidance. Submission retains drafts after failure and blocks duplicate requests and dismissal while pending. The existing platform-admin route guard remains in App.tsx.

| Area | Evidence |
| --- | --- |
| Responsive list | Browser1956 and final21228 recorded in PROGRESS: six light/dark320/768/1440 cases for actual-route read/search/cards/create cancellation/focus and count failure. |
| Current list and branding | Browser55687: four custom-purple light/dark320/1440x600 initial/cached read failures, counts fallback, search, mobile records, desktop native identity-link focus/href and dialog dismissal/focus. Parent inspected final desktop table. |
| Creation | Browser54271: four custom-purple320/1440x600 cases for discovery failure/manual creation, held500, pending Escape/Cancel protection, retained draft, retry/equal payload and destination. Final dark32064600 reviewed after footer ordering/outline correction. |
| Discovery/override | Browser35090 and final95713: four custom-purple light/dark320/1440x600 successful client-credentials discovery, read-only token, manual token override, flow switch, required authorization URL validation, held create500/retry, correct OAuth payload and destination. Parent inspected final dark320 selector/form/error/footer. |
| Tests | Three MCPServerForm tests61791 pass: retained draft/pending submission, discovery/manual client-credentials payload, persistent failed-discovery guidance and associated editable/read-only field labels. |
| Quality | Final scoped lint/full TypeScript11929 pass; touched-source diff check passes. |

The first discovery test caught a misplaced Redirect URL label association; corrected and rerun. TypeScript39917 reported the same pre-fix duplicate attribute; final11929 passes. Discovery blocks field edits while fetching. Loading no longer displays a premature empty-result warning.

Browser fixtures intercept mutations and use synthetic URLs; these prove UI behavior and payloads, not vendor OAuth connectivity. Disabled manifest import is an existing future product feature. Detail/connection routes, file-family reconciliation and application-wide release gates remain open.
