# Desktop List Scrolling

Scope: Organizations, Users, Roles, Config, Tables, Knowledge, Integrations, MCP Servers, Applications, Forms, Workflows, and Solutions list routes.

## Pattern

- `PageWorkspace` owns the desktop page-height boundary while preserving natural mobile page flow.
- `ListPageHeader` and route toolbars remain outside the scroll region so they stay visible on desktop.
- `PageScrollArea` owns the bounded list region. For card/grid lists it uses the default desktop overflow behavior.
- Desktop table routes set `lg:overflow-hidden` on `PageScrollArea` and keep `DataTable className="max-h-full"` so the table owns its sticky header/footer and body scroll.

## Route Audit

- Organizations: `PageWorkspace` wraps the route; `PageScrollArea` bounds the list body; desktop `DataTable` uses `max-h-full`.
- Users: `PageWorkspace` wraps the route; `PageScrollArea` bounds the list body and keeps pagination inside `DataTable` on desktop. Mobile cards continue to use natural page flow.
- Roles: `PageWorkspace` wraps the route; `PageScrollArea` bounds the list body and preserves the desktop `DataTable` footer pagination.
- Config: `PageWorkspace` wraps the route; `PageScrollArea` bounds the list body. Desktop table scrolling stays with `DataTable`; narrow cards remain natural.
- Tables: `PageWorkspace` wraps the route. The existing tab/list flex chain remains the scroll owner because the Tables page has split list/filter behavior and a claims tab with its own sizing.
- Knowledge: `PageWorkspace` wraps the route; `PageScrollArea` bounds document results. The desktop document table keeps footer pagination in `DataTable`; compact cards remain natural.
- Integrations: `PageWorkspace` wraps the route; `PageScrollArea` bounds the list body. The desktop table retains its own scroll; the mobile integration list no longer creates an internal scroll container.
- MCP Servers: `PageWorkspace` wraps the route; `PageScrollArea` bounds the list body. Desktop table scrolling stays with `DataTable`; compact cards remain natural.
- Applications: `PageWorkspace` wraps the route; `PageScrollArea` bounds results. Table mode disables the outer desktop overflow so `DataTable` owns table scrolling; grid mode scrolls the card list.
- Forms: `PageWorkspace` wraps the route; `PageScrollArea` bounds results. Table mode lets `DataTable` own scrolling; grid mode scrolls the card list.
- Workflows: `PageWorkspace` wraps the route; `PageScrollArea` bounds the result panel. The existing desktop sidebar split remains a local flex chain so the sidebar and result pane can share the remaining height.
- Solutions: `PageWorkspace` wraps the drag-and-drop route root; `PageScrollArea` bounds results. Table mode lets `DataTable` own scrolling; grid mode scrolls solution cards.

## Exceptions

- Detail routes are intentionally untouched.
- Shared layout beyond `PageWorkspace`/`PageScrollArea` is intentionally untouched.
- Tables and Workflows retain route-local flex chains for their split/sidebar layouts instead of forcing every nested panel through a single wrapper.
