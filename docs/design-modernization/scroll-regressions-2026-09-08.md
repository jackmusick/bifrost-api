# Scroll reachability and pagination correction

The first bounded-scroll pass was insufficient: checking outer-page overflow and counting scrollable descendants did not prove that the record collection could scroll. Table Detail's JSON previews produced scrollable descendants even when the enclosing record list was clipped. The user found this in the debug stack.

## Causes and fixes

- **Broken height propagation:** Table Detail's document section was a normal block inside an overflow-hidden workspace. It now passes the available height through a flex column with `min-height: 0`; the desktop table and document-card fallback each have a real scroll owner. Pagination remains non-shrinking.
- **Short desktop filters:** Stacking filter controls above records at 1100px could consume the content area. Desktop filters now sit beside records and scroll independently. Mobile retains stacked, natural page flow.
- **Mismatched breakpoints:** `PageWorkspace` becomes bounded at 1024px, while `useIsDesktop` changes many record layouts at 1280px. Integration cards and History's grouped records now own bounded scrolling between those widths. Workflow cards now receive a bounded parent between those widths as well. Forms, Apps and Solutions use the rendered table/card mode to select overflow behavior, so a remembered table preference cannot clip the card fallback after resizing.
- **Log and agent-run fallbacks:** Their 1024–1279 card branches now scroll inside the bounded workspace. In short History windows, filters and results share an outer bounded region below the heading/type switch; a minimum result height prevents controls from reducing messages to a sliver. Log pagination uses the table footer so it stays visible with long results.
- **Outside outlines:** Agent card rings were drawn outside their boxes, where the scroll container clipped the top and left edges. The shared agent card surface now draws its ring inside the box.
- **Independent pagination implementations:** Role assignment tables supplied a footer even for one page, unlike History. They now show paging only when a previous/next page exists. `PaginationFooter` supplies Audit-style summary text and outlined Previous/Next buttons to the offset/cursor wrappers. Document tables retain their page-size selector; redundant single-page navigation buttons are hidden.

## Audit method

For each populated table, add many browser-only duplicate records, locate the actual record collection's scroll owner, scroll it to its end, and check the final row against both that owner and the main viewport. Account for the collection itself being the scroll owner (document `ul`) and choose the final group when grouped records contain multiple lists. A child JSON/code preview is not evidence of table scrolling. Empty data states are source-reviewed, not claimed as populated acceptance.

Check desktop table mode, the 1024–1279 card fallback, remembered table mode after resizing, filters open/closed, external pagination, and short windows. Inspect `DataTable`'s defaults before flagging a missing height class: its root already has `flex flex-col min-h-0 max-h-full`. Audit and Fleet's existing table chains passed actual long-row checks; absence of those classes at a call site alone was not a defect.

Persistent browser regressions in `desktop-scroll.admin.spec.ts` now exercise real wheel input on Table Detail at 1440×600 and 1100×600 with filters open and closed. They assert final-record reachability, a non-main scroll owner, usable content height, and visible heading/page-size controls. Existing long/short Configuration and mobile-flow tests remain in the same suite.

The follow-up live-data stress matrix covers populated list/detail record surfaces at 1440×600 and 1100×600, supplemented by the card fallback checks. Temporary browser duplicates do not modify backend data. Empty Solutions, Knowledge, and MCP lists still lack populated live acceptance; their source compositions and relevant focused unit tests are checked separately.

Confirmed long-record surfaces include Organizations, Users, Roles, Configuration, Tables list/detail, Integrations, Audit, role assignments, Workflows, Forms, and History. Intermediate-width Integration/History cards and resized Workflow/Form cards were checked separately. One initial script falsely rejected document cards because it started looking for a scroll owner at the list parent, and another checked the first History group after scrolling to the last; both probes were corrected. Passing scroll geometry from those corrected probes is the acceptance evidence.

Final log stress checks at 600px height left 177px for desktop log rows and 158px for intermediate-width log cards, with the final message reachable. Agent-run populated live data was absent; its shared footer/fallback changes have source review and eight focused passing tests. Full client TypeScript/lint and the combined ten-file, 99-test focused batch passed. Eight browser scrolling regressions passed.
