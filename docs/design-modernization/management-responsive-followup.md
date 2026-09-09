# Management layout and pagination follow-up

## Scope and decisions

Config and MCP Servers are centered at a maximum 1400px; Files and Entity
Management use 1600px for their multi-pane workspaces. Config switches to labeled
records below 1280px, with its scroll owner retained through that breakpoint.
Files retains its three-pane layout only at 1440px and above; narrower layouts
use the share/details sheets and labeled file records. Entity assignment remains
available in a sheet below 1280px. Long keys, URLs, filenames and organization
labels remain readable. MCP header actions stay together below the title until
there is enough room for the desktop arrangement.

The passkey button stays in the main header from 640px upward. Previously it
was grouped with secondary status indicators below 1280px, causing an unnecessary
extra row. Small phones retain the status row to preserve touch target sizes.

## Pagination and action audit

| Surface | Finding and resolution |
| --- | --- |
| Users and Roles | Already shared ListPagination; sticky action headers had a different background. Match the muted header surface and compact Actions column. |
| Role detail tabs | Use ListPagination through ConsumerTab; keep a count summary on single-page lists. |
| Organizations | Previously no pagination. Paginate the filtered local dataset in 25-row pages, reset on filters, clamp after data changes. |
| Knowledge | Replace remaining direct legacy pagination primitives with PaginationFooter. |
| Audit, History, Logs, Agent Runs | Use the shared PaginationFooter with cursor-specific summaries/navigation. Cursor endpoints cannot promise total counts. |
| Documents | Shared footer retains its page-size selector. |

ListPagination shows its summary but omits unnecessary navigation buttons for a
single page. Source search found no remaining application consumers of
PaginationPrevious/PaginationNext; their reusable primitive exports remain for
compatibility. Wizard Next buttons are task progression, not table pagination.

## Verification

- Parent browser review: Config, Files, MCP Servers, Entity Management, Users,
  Roles and Organizations at 390, 1024 and 2560px; intermediate 1440px reviewed.
- Synthetic config, inactive MCP template and file share added to the debug stack
  for populated review. Mobile share selection and long-filename upload passed.
- Passkey main-row alignment checked at 640, 768, 1024 and 1280px with a mocked
  empty passkey list/browser support; this is a layout test, not WebAuthn enrollment.
- Scoped component tests cover pagination/role consumers/organization filtering,
  config, MCP form, entity controls, file explorer/listing and passkey affordance.
- TypeScript and scoped lint passed. Mechanical design detector reported no findings.
- No full backend or full application E2E suite was run for these UI changes.

Integrations remains unchanged pending mockup review. The proposal uses uploaded
logos, compact cards and an optional table view; shown services, logos and mapping
counts are illustrative. It does not claim live connection health from setup data.
