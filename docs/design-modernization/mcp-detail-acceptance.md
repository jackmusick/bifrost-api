# MCP server detail acceptance

Status: UI Verified. Scope: `/mcp-servers/:id`, its organization connections, settings/manifest tabs, new-connection dialog and deletion confirmation. The connection editor is reviewed separately.

Connection summaries use responsive cards with explicit availability, status, tool count and native management links. Settings use wrapping definitions and keyboard-focusable, bounded JSON. Tabs fit narrow screens. The heading uses the display font and back navigation is a native link. The platform-admin guard remains in App.tsx.

| Area | Evidence |
| --- | --- |
| Settings and metadata | Current browser8936: four custom-purple light/dark320/1440x600 tab bounds, connection card bounds, settings navigation, long metadata wrapping/keyboard focus and manifest explanation. Parent inspected dark320 metadata and light1440 cards. |
| Read recovery | Current44906: four matching cases for initial500/retry without false missing state, cached refresh500 with retained records and successful retry. Parent inspected dark320 warning/header/tabs. |
| Navigation | Final95620: four matching cases for native breadcrumb href, connection management keyboard activation and destination heading. Earlier16345/80970 failed only because the desktop sidebar and breadcrumb shared the same name; scoped assertion to breadcrumb. |
| New connection | Browser20661: four custom-purple light/dark320/1440x600 org lookup failure/retry, held creation500, disabled fields/Cancel, Escape protection, retained draft, focused inline error, footer viewport bounds and retry destination. Two component tests67973 pass. Parent inspected dark320 and light1440. |
| Server deletion | Browser89975: four custom-purple light/dark320/1440x600 held500/retry/success, pending Escape protection, error/footer bounds and return to list. Parent inspected light320. |
| Quality | Final detail lint/full TypeScript14013 and touched-source diff check pass. |

Fixtures intercept mutations and use synthetic records; no actual server deletion or connection creation occurred. Manifest per-server export is an existing future feature, not a migration deliverable. External OAuth connectivity, the connection editor, file-family acceptance and whole-application release gates remain separate.
