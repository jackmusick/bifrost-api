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
