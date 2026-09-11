# Bifrost product design contract

Canonical authority: `gobifrost/design-system` at `11da72e`. The user approved bringing its existing identity into the complete platform, with custom-brand support and preservation of behavior. This is an operational product; hierarchy and reliable interaction carry the character.

## Foundations

Use Inter for interface text, Prompt for restrained identity/display, and JetBrains Mono for code and measurements. Default Bifrost dark canvas is #08090b, surface #0a0c0f, primary #2fd4d4; light canvas #f7f9fa, surface #ffffff, primary #087f86. Semantic colors retain independent success/warning/error meaning. Follow canonical tokens for 6px controls, 4px surfaces, 8px feature radii and compact/comfortable/spacious density. Elevation belongs to floating layers; tonal surfaces and hairlines establish ordinary hierarchy.

## Branding

Existing runtime branding remains authoritative. Derive action/hover/focus/contrasting foreground and activity-gradient roles from the selected custom brand. Default identity uses the Bifrost spectrum. Custom brands use coherent tonal or hue-related stops instead of inheriting an unrelated rainbow. Validate light/dark contrast. Do not recolor semantic errors or successes into brand accents.

## Motion

Feedback 120ms, disclosure 220ms, route at most 360ms, genuine activity 1600ms. Preserve reading position during streams. Spectrum/brand-gradient motion conveys actual route or execution activity, never invented completion percentages. Connection state is distinct from execution outcome. Reduced motion removes loops, translation, blur and clipping while retaining legible state.

## Composition and compatibility

Shared header/action/filter/table/inspector patterns provide consistency, with each page designed for its actual task. Avoid proliferating cards and competing primary actions. Preserve route terminology and navigation expectations. On mobile use focused panes, deliberate disclosure, accessible controls and appropriate table alternatives; do not shrink a desktop workspace wholesale.

Retain existing Radix-backed component APIs and V1 runtime exports. Source-copy registry components are visual references, not automatic replacements for richer product contracts. Preserve portaled overlays, keyboard semantics, refs and compound components. Keep customer-authored content outside blanket page-layout selectors.

## Verification

Every coverage-ledger item requires an individual source review and applicable rendered evidence. Test themes, branding, widths, states and important interactions. A build or token replacement is not proof that a page has been redesigned.


## Mobile data presentation

Mobile acceptance means an easy-to-use, readable composition, beyond preventing page overflow. Review the user's task at the narrow viewport: show record identity and the highest-priority value together, retain the remaining labeled values, and make sorting and actions directly usable. Prefer record summaries for dense report/list tables where sideways reading separates labels from values. Keep desktop comparison tables when useful; both representations must share data, ordering, permissions and actions. Test the intermediate widths where the sidebar reduces available content width. A horizontal scroller alone is not evidence that a dense data page is mobile-friendly.

Selected control groups use tenant primary tokens. Semantic green indicates a meaningful positive status or outcome; audit hard-coded green selection treatments independently from success indicators.


## Home, collections, and execution

Home combines accessible apps, forms, and chat-enabled agents, with personal pins and collections plus administrator-curated shared collections. Organization and resource type must remain visible when browsing across customers. Collections organize existing access; they do not grant it. Use the existing Lucide library for collection icons.

Execution is result-first. The full page and preview share Result, Input, Logs in that order, defaulting to Result. Logs are optional supporting detail, with wrapping messages and secondary timestamps; never reserve a blank log column. Never infer workflow steps or percent completion from plain logs. Use an indeterminate brand-aware activity trace while running, respect reduced motion, and preserve manual inspector choices when results arrive. On desktop, selected content scrolls within the available height; on mobile, use full-width sections. History preview must preserve table scroll bounds and keep shared pagination visible.

See [Home and execution experience](docs/design-modernization/home-execution.md) for behavior, verification, and rollout details.

### Execution section headings and log severity

Run Activity, Execution Context, Runtime Variables, and Usage use the shared ExecutionSectionHeading: title case, foreground display text, a primary-colored Lucide icon, and an optional muted description. Uppercase metadata labels are not section headings.

Readable activity and detailed logs share LogEntryRow severity framing. A 3px leading stripe uses semantic info, warning, danger, or muted-debug tokens, independent of custom branding. Preserve text/icon severity cues as well as color. The newest-message highlight indicates recency and must not override severity. Keep filtering, traceback grouping, copying, and follow-scroll behavior in the detailed log panel.
