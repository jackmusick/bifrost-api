# History density refinement — 2026-09-08

Desktop History places Workflows/Agents next to the title using the shared
ListPageHeader title accessory. Search, workflow, organization, date and Logs view
controls share one wrapping toolbar. At 1280px and 1440px viewport widths the
controls fit on one line. The status tabs remain directly above the results.

Mobile keeps history types on their own full-width row and exposes secondary
filters through the existing Filters disclosure. No controls are removed solely
to make a screenshot fit.

The Show local checkbox was removed. The API still supports legacy local-runner
records; History retains its existing default `excludeLocal: true`. This change
does not remove backend compatibility or change which records appear by default.

The workflow overflow action now says Edit, matching the existing edit dialog.
Managed workflow restrictions and action behavior are unchanged.

Validation: 31 existing History/workflow tests passed. Parent screenshots reviewed
at 1280px, 1440px and 390px, including expanded mobile filters. Browser checks
confirmed Logs/Agents switching and reaching the last desktop table row with
window scroll remaining zero. TypeScript and scoped ESLint passed.

Pagination follow-up: History still placed the shared controls inside a shaded
DataTableFooter. It now renders the same footer below the table as Audit, with
one shared desktop/mobile instance definition. The desktop results region uses a
bounded flex column so pagination stays visible while the table body scrolls.
Parent browser verification reached the last row with window scroll zero and
pagination in the viewport; 18 History tests and scoped lint passed.
