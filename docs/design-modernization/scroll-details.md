# Detail/Admin Scroll Audit

## Scope

This pass covers desktop bounded scrolling for detail and admin routes owned by the scroll-details slice only. List pages, shared layout primitives, agents, editors, forms, and reports remain outside this slice.

## Scroll Owner

- Role detail keeps the role header and tab list persistent. Each tab body is bounded on desktop; role assignment tables keep their own `DataTable` scroll context.
- Solution detail keeps breadcrumbs, header actions, setup notices, and section tabs persistent. Overview, contents, configuration, and exports use the page scroll region. Access keeps `DataTable`-owned scrolling.
- Table detail keeps the table header, search, and filter controls persistent. The documents region is height-constrained so `DocumentRecordList` and its `DataTable` can own desktop table scrolling.
- Integration detail keeps the integration header persistent. Overview controls and mapping tabs live in bounded content, with a minimum usable tab height so short desktop windows can scroll to mappings. Mapping search and auto-match controls stay visible within the mapping card while its organization rows scroll; configuration overrides use page scrolling.
- MCP server detail keeps breadcrumbs, header actions, and server tabs persistent. Connection cards/settings/manifest scroll inside the active tab body.
- MCP connection edit keeps breadcrumbs and Save/Cancel/Delete controls persistent. The editable form panels scroll in the remaining desktop viewport.
- Event source detail keeps the source header/actions, metadata, and subscriptions/events tabs persistent. Subscription and event tables keep their own scroll context.
- Settings keeps the page header, mobile nav toggle, and desktop settings nav persistent. The active settings panel scrolls and still resets to top on section change.
- User settings keeps the header and tab strip persistent. The active user settings panel scrolls in the remaining desktop viewport.

## Changes

- Applied `PageWorkspace` to owned detail/admin page shells.
- Applied `PageScrollArea` to content regions where the page owns scrolling.
- Used `PageScrollArea` with `lg:overflow-hidden` where a child `DataTable` or purpose-built row region owns sticky header/footer or record scrolling.
- Added flex/min-height chains to role tabs, document records, event source tabs, and user settings tabs so bounded desktop height propagates to the scrolling child.

## Exceptions

- Mobile keeps natural document scrolling because `PageScrollArea` only applies bounded overflow at `lg`.
- Data table routes avoid double scrollbars by letting `DataTable` remain the only scrollable element for table bodies and footers.
- Event source metadata remains above the tab scroll region so source actions and provider status stay visible while reviewing event history.
