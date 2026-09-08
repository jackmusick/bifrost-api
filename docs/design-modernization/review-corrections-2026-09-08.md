# Review corrections — September 8

This follow-up addresses hands-on review of the debug stack after the broad migration. The migration changed every route family, but that did not mean every layout and interaction was finished. Entity Management, integration density, and shared navigation behavior needed further work.

## Shared behavior

- Platform route transitions now remount page content, preserving the sidebar/header shell. A live navigation from History to Users preserved the same sidebar DOM element and scrollTop of 452px.
- A record row opens its primary item where that action is unambiguous. Native links/buttons remain keyboard entry points. Nested controls and text selection do not activate the row; modified and middle clicks retain new-tab behavior where an href exists.
- Config, workflow history links, editable forms, applications, tables, and knowledge now use the same row convention. Assignment controls and reports do not invent a primary action.
- Desktop History grows to content within the remaining viewport and scrolls the table body when necessary. The live populated case measured a 417px scroll region with 638px content; the page itself did not overflow. Mobile keeps natural page scrolling and record cards.
- Pagination reflects the data source. Role user assignments and Audit Log are both paginated; other assignment tabs can contain complete collections. Empty assignment pages now retain Previous/Next recovery instead of dropping their pagination controls.

## Page corrections

- Agent cards no longer clip their top edge inside an unnecessary nested scrolling container.
- Integration Mappings has organization/entity search, filtered counts, clear-search recovery, and compact responsive rows. Auto-match still operates on the full organization set. It requires a configured entity data provider, as on main; missing configuration is now explained. The integration overview's unconfigured OAuth panel is also more compact.
- Entity Management exposes dependencies as a visible diagram button, with destructive actions aligned right in overflow. Dense dependency graphs focus the root at 80% instead of automatically shrinking labels to 15%; manual Fit graph still shows the entire graph. Resizing no longer overwrites manual pan/zoom.
- The editor workflow dropdown renders above the editor at z-index 200. Playwright hit-testing confirmed the open menu was the topmost element.
- Default branding previews the canonical teal and full Bifrost spectrum. Saving unrelated branding fields preserves the distinction between a default color and a custom one. Color and logo reset persistence now distinguishes omitted repository arguments from explicit null.

## Runtime configuration

The debug instance uses a personal OpenRouter connection and the `~deepseek/deepseek-v4-flash-latest` model alias for primary, summarization, tuning, and default chat. A live completion resolved to `deepseek/deepseek-v4-flash-0731`. The synthetic service assistant explicitly uses that profile. Image/video assignments are unset. No credentials are in this document or the repository.

The user's live branding selection was preserved. Browser reset checks intercepted only the test browser's branding responses; database persistence is covered separately by backend tests.

## Verification

- `./test.sh client unit` with the 18 affected shell, row, mapping, assignment, editor, list, fleet, and branding test files: **145 passed**.
- DependencyGraph, DependencyGraphViewport, DependencyGraphControls focused tests: **7 passed**.
- Client `npm run tsc` and `npm run lint`.
- Parent Playwright review at 1440px and 390px: agent cards, History, Entity Management, dependency graph, integrations, branding. Interaction checks cover mapping search/clear, sidebar lifetime/scroll, graph initial/manual framing, and editor menu stacking.
- Impeccable detector on EntityCard, IntegrationMappingsTab, Branding, ExecutionHistory: no findings.
- `git diff --check`.

Backend verification:

- `./test.sh tests/unit/test_branding_repository.py`: **6 passed**.
- `./test.sh tests/e2e/api/test_misc.py::TestBranding::test_update_terminology_does_not_rewrite_color_and_color_reset_persists`: **1 passed**, including a GET after reset to prove persistence.
- `./test.sh quality api`: **0 errors, 0 warnings**.

 The full pre-PR gate is not repeated for this correction pass; no PR is opened or merged. The debug stack remains running.
