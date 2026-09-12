# Knowledge workspace

Knowledge follows the contained Files workspace pattern without its directory
and policy layers. Documents are the primary objects: a readable title and short
content preview lead each row; namespace and organization scope wrap beneath the
title rather than competing for narrow table columns. The workspace owns search,
filters, selection, import/export, and pagination.

Opening a document attaches an editor to the list. At narrow widths, the editor
occupies the workspace, while the site's navigation remains available. Document
content uses the existing Markdown editor and metadata viewer. Save errors,
conflict replacement, organization permissions, and bulk scope changes retain
their existing contracts. Selection controls are a deliberate bulk-edit mode;
ordinary row interaction opens the document.

## Verified checks

The Knowledge workspace finish was verified with 13 component tests across
`Knowledge.test.tsx`, `KnowledgeDocumentDrawer.test.tsx`,
`KnowledgeDocumentList.test.tsx`, and `KnowledgeEditorPane.test.tsx`. The
Knowledge acceptance Playwright run passed both tests, including setup. Live review
used desktop 1440px and mobile 390px screenshots against the synthetic namespace
`ui-review-knowledge` (three documents). Final reviewer disposition: ship, with no material
findings. Scoped lint and TypeScript checks passed. Full suites and the pre-PR gate were
not rerun for this scoped refinement.

## Tables follow-up

The existing document table has a custom Copy ID button and per-row raw JSON
disclosure. The next Tables pass should bring filtering, records, and inspection
into one workspace. Keep tabular comparison for actual fields, move full record
inspection out of expanding rows, and use the shared hover-copy presentation for
IDs. Formatted data should be the default; raw JSON belongs in an explicit view
inside the record inspector. Preserve complete raw data access and editing.

## Review refinements

The workspace is content-sized when browsing a short list, capped by available
space; an open editor gets a bounded workspace with fixed Save/Cancel controls.
The feature frame is a flex column so headers and footers consume their own
space instead of extending the editor beyond the visible boundary. Scope is
flush on the left of the toolbar. All Namespaces uses the shared searchable
Combobox; its trigger stays one line, while the popup shows complete names.

Select is a switch. In selection mode, whole document rows toggle selection,
with a checkmark in the existing icon slot and the normal selected surface.
There are no selection checkboxes. Scope, namespace, and date occupy compact,
consistent positions on the left of each row, adapting to two lines when narrow.
Preview text uses MarkdownContent's noninteractive preview variant; the API's
200-character excerpts may still end mid-syntax.

Refinement checks: 13 scoped component tests, desktop/mobile browser checks for
namespace search and whole-row selection, visible Save controls, and no page
horizontal overflow; scoped lint and TypeScript. The persisted Knowledge
acceptance spec is also rerun; broader suites are outside this refinement.

Refresh feedback lives in the toolbar icon beside Select; it spins only while
refreshing and respects reduced motion. Background refresh retains rows and does
not insert a text/status row. On larger screens the embedded Markdown editor
shares remaining height with the collapsed Metadata control; expanding Metadata
reveals a bounded scroll region. Save/Cancel remain fixed below the body.
Checked with 13 scoped Knowledge/editor tests, TypeScript, scoped lint, and live
desktop/mobile checks including collapsed Metadata visibility without outer-body
scrolling and expanded metadata content. Full E2E was not repeated for these
local feedback/layout changes.

Desktop Scope, Search, and Namespace now form adjoining toolbar sections with
subtle dividers. Search takes remaining space; actions retain their own padding.
Mobile keeps the compact search/filter layout and allows actions to wrap.
Verified with eight Knowledge tests, scoped lint, TypeScript, and live desktop
and mobile checks for filtering, selection, editor controls, and overflow.
