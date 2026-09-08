# Page scrolling contract

Follow-up: [record reachability corrections](scroll-regressions-2026-09-08.md) supersede the initial visual-only acceptance for Table Detail and intermediate-width card layouts.

Desktop workspaces keep navigation and primary page controls available while content uses the remaining viewport. Small result sets stay compact; long results scroll. At widths below `lg`, ordinary pages return to natural vertical flow and mobile record layouts. Editors, chat, and execution consoles retain their purpose-built pane scrolling.

## Composition

Use `PageWorkspace` for the page shell, a non-shrinking header/control group, and `PageScrollArea` for the body. Label multiple scroll regions by their purpose. Do not set a fixed pixel height based on one screen or fill a short table with empty rows.

For prose, cards, settings and reports, the page body owns overflow. For a standalone `DataTable`, use a flex column with `min-h-0` and a definite available height through every intermediate wrapper; set the outer `PageScrollArea` to `lg:flex lg:flex-col lg:overflow-hidden`. The table owns scrolling and its sticky header/footer. Keep external pagination outside that scroll area and non-shrinking. Avoid nested vertical scrollbars for the same records.

For multi-pane tools, each work area can scroll independently. Check short desktop windows: keeping every summary fixed must not reduce the working area to zero. Move secondary summaries into bounded content when necessary. Dialogs retain their existing independent viewport constraints.

## Route coverage

The 64-entry route inventory was reviewed by page family. Duplicate layout entries, parameter aliases, and public callbacks do not each require a new scroll wrapper.

| Family | Desktop scroll owner | Evidence in this pass |
| --- | --- | --- |
| Dashboard; ROI and usage reports | Body below heading and report controls | Rendered desktop/mobile; reports also short desktop |
| Workflows, forms, organizations, users, roles, solutions, configuration, tables, knowledge, integrations, MCP servers | Records below list controls; table body where applicable | All list routes rendered desktop/mobile; long and short Configuration fixtures tested |
| History and Audit Log | Table body; filters and pagination remain available | Rendered desktop/mobile; Audit Log also short desktop with 50 records |
| Role and table details | Active tab/record table | Seeded detail routes rendered desktop/mobile and short desktop |
| Integration detail | Mapping records or active configuration content | Seeded detail rendered desktop/mobile; short-window clipping caught and corrected |
| Solution details, MCP server/connection details, event source details | Active content/tab, with child tables owning record scrolling | Source-reviewed; focused unit coverage. Debug stack has no populated records for these detail routes |
| Events list | Source list/detail workspace | Empty route rendered desktop/mobile; populated detail source-reviewed |
| Agents | Fleet results; detail tab; review/tuning work area; run detail body | Fleet, new/detail/settings/runs, empty review and tuning rendered desktop/mobile; fleet/settings also short desktop. Populated review/run/tuning states source-reviewed |
| Entity Management | Entity list and assignment panels | Rendered desktop/mobile and short desktop |
| Settings and User Settings | Active settings panel | Rendered desktop/mobile; Branding also short desktop |
| Diagnostics | Active tab content | Rendered desktop/mobile |
| Workflow/form execution | Parameters or form body below page controls | Seeded execution routes rendered desktop/mobile |
| Form designer | Palette, fields and preview panes | New/edit rendered desktop/mobile; edit also short desktop |
| Execution detail | Detail body and existing log pane | Seeded execution rendered desktop/mobile and short desktop |
| Files and app editor | Existing explorer/editor panes | Files and new app rendered desktop/mobile; existing editor pane structure source-reviewed |
| Chat and artifacts | Existing conversation panes; artifact body below search | Rendered desktop/mobile |
| Login/setup/invitation/MFA/device/callback routes | Natural standalone page flow | Source-reviewed; outside platform workspace contract |
| V1/V2 app runtime/preview and embedded forms | Host/app-owned content scrolling | Existing ownership preserved; source-reviewed |

## Verification

The browser sweep captured 42 route states at 1440×900 and 390×900, plus 11 selected states at 1440×600. All normal desktop route captures had zero outer-main overflow; no route had horizontal document overflow. Fleet and Audit tables were additionally stressed with 80 browser-only cloned rows at 600px height: the final row remained reachable and outer-main overflow stayed zero. Screenshots and scroll geometry were inspected together: zero outer overflow alone does not prove content is reachable, as the initial short Integration Mappings capture demonstrated.

`client/e2e/desktop-scroll.admin.spec.ts` checks long Configuration records at desktop heights 900 and 600, pinned heading/table header, last-record reachability, compact short tables, and natural mobile card scrolling. It uses intercepted synthetic records without modifying server data. Dynamic pages without seeded resources are explicitly source-reviewed above, not claimed as populated browser acceptance.

See [list implementation notes](scroll-lists.md) and [detail implementation notes](scroll-details.md). The debug stack remains running for review; this work does not merge the modernization branch.

Final checks: client TypeScript and ESLint passed; the Fleet suite passed all 20 tests after removing its obsolete unbounded-height expectation. The focused list batch passed 81 tests, the detail batch passed 100 tests, and the four desktop/mobile scrolling browser regressions passed. The broader parent batch passed 178 tests before that Fleet expectation was corrected. These batches overlap and are not reported as a unique total. Full pre-PR validation was not rerun for this frontend scrolling pass.
