# MCP connection editor acceptance

Status: UI Verified. Scope: `/mcp-servers/:serverId/connections/:connectionId/edit`.

The editor retains credential opt-in/masking, availability flags, OAuth/client-credentials flows and per-tool settings. Mobile tool records wrap names and descriptions with labelled keyboard-operable checkboxes. Native breadcrumb navigation, display heading, semantic status/action colors and 44px actions use the shared system. The existing platform-admin route guard remains in App.tsx.

| Area | Evidence |
| --- | --- |
| Read recovery/catalog | Current67369: four custom-purple light/dark320/1440x600 initial read500/retry, labelled tool click/keyboard selection and footer action bounds. Parent inspected dark320 tool record. |
| Credentials | Current23512: four matching cases for opt-in secret editing, masked default, named reveal/hide, removal on opt-out and44px controls, plus catalog/keyboard/action checks. All entered values synthetic. |
| Save/partial failure | Current50498: four matching cases for held connection PATCH500 (no tool requests), retained draft and focused error, then tool PATCH500 after connection success, retained selections/refetch, final retry with equal connection payload and successful tool patch. Parent inspected dark320. |
| Catalog/disconnect | Current87838: four matching cases for held catalog500/pending locks/retry, subsequent read500 with explicit cached warning, retained client/tool draft and read retry, held disconnect500/pending locks/retry and disconnected UI. Parent inspected dark320. |
| Activation | Current36350: four matching cases for held client-credentials activation500, inline retry and successful connected-state refresh. Parent inspected light320. |
| OAuth start | Current35362: four matching cases for pending/Escape protection, start500/blank-popup cleanup, retry/synthetic authorization URL and error/footer viewport bounds. Parent inspected dark320. |
| Delete | Current52714: four matching cases for held delete500, pending protection, retained confirmation/error, retry and dismissal. Parent inspected light320. |
| Quality | Full scoped lint/TypeScript88085 passes. Final scoped lint54065 and diff check pass after awaiting catalog refetch. |

Save, catalog refresh and disconnect share a synchronous mutation guard; editing and Save/Cancel/Delete are disabled while these operations are pending. Activation has its own pending control, and OAuth startup owns its dialog. Background failures preserve drafts. Semantic Connected and destructive controls respect theme tokens. OAuth/delete dialogs have bounded scrolling content and fixed actions.

These are UI acceptance fixtures with intercepted writes, synthetic URLs and stubbed authorization windows. They do not prove real vendor token exchange/callback completion; existing protocol behavior is retained. Manifest features belong to the separate server detail. Application-wide tests/build, family/file acceptance and delivery remain open.

Final save regression5341 repeats all four connection/partial-tool failure and retry cases after the shared mutation guard changes; all pass.
