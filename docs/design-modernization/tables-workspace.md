# Tables workspace

Tables extends the Files and Knowledge workspace language, including the details
resolved during their review. This is an operational surface: fast comparison,
readable records, and contained editing take priority over decoration.

## Workspace contract

- Tables and Custom Claims belong to one frame with compact tabs.
- Scope is flush left. Search joins it without an extra input box on desktop.
  Actions remain a distinct compact group; mobile wraps without clipping.
- Short lists use only their content height. Longer lists scroll within the
  remaining desktop space, with controls and document pagination outside rows.
- Select is an explicit switch for catalog export selection. Whole rows select
  in that mode and open normally outside it. There are no permanent checkboxes.
- Icons align with titles. Descriptions use the shared Markdown preview.
  Scope and date form a compact, consistent metadata group below the title.
- Refresh uses a spinning toolbar icon, respects reduced motion, and retains
  existing content. It never inserts a shifting refresh-text row.

## Records and editing

Actual scalar fields remain comparable in the desktop data grid; nested objects
are summarized by field/item counts. Identity fields take priority over arbitrary
JSON object key order when choosing the three preview columns. Narrow panes use
record summaries instead of squeezing the data grid.

Opening a record attaches an animated inspector to the workspace. Data is
formatted through the shared PrettyInputDisplay. Complete JSON remains available
in an explicit inspector tab; there is no expanding JSON section in every row.
The same HoverCopyText component presents IDs in rows and inspector headers,
with its copy hint above the text and keyboard/touch support.

Table settings and document edits share their existing mutation and validation
logic with embedded variants. Footer actions remain fixed; the editable body
scrolls. Collapsed record Metadata sits above the footer, with its own bounded
expanded content. On mobile the inspector replaces the workspace body rather
than the screen; opening it positions the workspace beneath site navigation.

Search remains explicitly limited to the current document page. Filters query
the whole table. Pagination retains rows while the next page loads. Existing
solution-managed restrictions, query scope isolation, save errors, retries,
delete confirmations, and solution-aware back navigation are preserved.

## Review data and verification

The debug-only table ui_review_table_workspace contains 32 synthetic customer
records with scalar, Markdown, array, and nested object fields. It is left in
the debug stack for review; no production records were changed.

Scoped verification covers catalog selection, recovery, retained pagination,
record inspection, copy failures, JSON validation, settings, claims, and saves.
The persisted browser acceptance covers table create/edit and document
create/inspect/JSON/edit/delete, followed by table deletion. Live layout review
covers desktop, narrow mobile, short desktop windows, internal scrolling, and
visible editor footer controls. Full suites and the merge gate are outside this
scoped follow-up; the branch remains unmerged.

Verified commands: ./test.sh client unit -- Tables.test.tsx TableDetail.test.tsx
DocumentRecordList.test.tsx TableDialog.test.tsx TablesClaimsTab.test.tsx
DocumentDialog.test.tsx DocumentInspector.test.tsx HoverCopyText.test.tsx
(51 tests); ./test.sh client e2e e2e/table-records-acceptance.admin.spec.ts
(two tests including authentication setup); scoped ESLint; npm run tsc.
Claims and catalog/record tests were repeated after their final local changes.
For Playwright passthrough, pass the spec directly without a redundant --.

Navigation refinement: entering a table retains the catalog's Data Tables
header and frame position. Table identity and the solution-aware return link
move inside the frame as a breadcrumb. Loading/error states use the same shell.
Primary workspace actions share WorkspacePrimaryAction across Tables, Claims,
Knowledge, and Files, aligned flush with the trailing toolbar edge.
Verified with the affected page tests, FilesExplorer tests, desktop/mobile live
screenshots, scoped lint, and TypeScript. The earlier CRUD acceptance was not
repeated for this presentation-only refinement.

Header alignment refinement: catalog tabs and detail breadcrumbs now share
WorkspaceHeader (48px). Table descriptions open from About This Table instead
of adding a helper-text row. Verified identical header bounds before/after
navigation at 1440px and 390px, description popup containment, breadcrumb
navigation, and browser Back. All 16 scoped unit tests, ESLint, and TypeScript
passed. Desktop/mobile screenshots reviewed.
