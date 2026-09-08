# Events acceptance

Current route status: all three Events routes UI Verified. All three routes preserve the platform-admin wrapper in App.tsx. This document records frontend acceptance, not server authorization or final release verification.

## Source list: `/event-sources`

Current list uses mobile source cards and a desktop table, native identity links and shared EventSourceActions. Search, status tabs, scope filter, refresh, create, edit, delete and activation remain available.

Evidence:

- List shell/read/delete recovery: events-source-menu-recovery.cjs68433, four theme/width cases with parent mobile review.
- Shared source actions and focused destructive color: source-detail-menu-check.cjs79038, four cases; menu keyboard focus, edit/cancel, held delete failure/retry.
- Desktop native identity link: six list tests92238 and creation-result links in24618/53533.
- Schedule creation:44997, four cases covering cron, pending protection, failure/draft retention and retry; topic reference help69442.
- Webhook/topic creation and option reads: source-create-options-check.cjs24618, four320/1440 light/dark cases with custom purple and reduced motion; initial loading, adapter/integration/topic failures, retry, retained custom topic and identical save-retry payloads.
- Actual Graph schema creation: source-create-graph-check.cjs53533, four320/1440 light/dark cases. Empty adapters and integrations refresh successfully; missing organization blocks submission and focuses error; selected user/resource and change types produce the expected scoped payload; held failed save retains values and blocks dismissal; cached adapter refresh failure keeps choices available and retry preserves selection. Parent inspected mobile empty/cached options and desktop selected Graph configuration. All writes intercepted.

Source activation is now covered by final98781 below. Creation and list acceptance are complete for UI scope.

## Source detail: `/event-sources/:sourceId`

Current source detail preserves identity/scope/status, active state, provider health, subscriptions/events tabs, full webhook address copy, edit/delete, resubscribe and source refresh. Secondary actions use the same menu as the list.

Evidence:

- Source detail layout/delete protection:74410; webhook address full-text copy denial/retry16979 and final mobile51078; current source menu79038.
- Graph/topic presentation: events-source-matrix-check.cjs captures exist; parent inspected prior Graph/topic/brand presentation. This script does not prove resubscribe mutations.
- Live events:29758, four current actual-client-WebSocket cases prove new rows, source count updates, open-event status completion, disconnect presentation with retained records and reconnect. Parent inspected mobile reconnect and desktop updated count.
- Subscriptions:91354/91286 prove responsive rows, read retry, active toggle failure/retry, edit and delete guards. Final56251 proves fixed edit footer at320/1440x600; parent reviewed.
- Edit schedule/webhook:15793. Current actual Graph edit80390 proves metadata recovery, scoped dynamic queries, failed-save retention and fixed actions/error focus.
- Organization changes: source-edit-graph-context.cjs32324, four cases. Shared DynamicConfigForm clears prior dynamic user/resource choices, retains static change types and submits the newly selected tenant resource.17 dynamic tests23032,24 create/edit consumer tests23738, lint95242 and full TypeScript42763 pass. Initial edit values preserved; integration changes additionally covered by regression test.

Source activation and Graph resubscribe are now covered by final98781 below. Source detail acceptance is complete for UI scope.

## Event inspector: `/event-sources/:sourceId/events/:eventId` — Verified

Deep-link ID opens the inspector even outside the current list window, and close returns to the source URL. Current App.tsx preserves its platform-admin gate.

Evidence:

- Deep-link loading/error/not-found and close navigation captures; initial/cached event/delivery reads7152 include actual DeliveriesTable, header expansion and clipboard failure/retry.
- Deliveries28668/7083: per-row retry/send failures and exact payload, navigation links, copy recovery, mobile/tablet and custom-brand/reduced-motion behavior.
- Live status29758: actual client event_updated handler updates open inspector status.
- Final event-detail-matrix.cjs96899:20 scenarios across320/1440 light/dark, custom purple and reduced motion. Nested object expansion, large array/long text with copy denial/retry/exact data, HTTP403/404 generic recoverable reads and source navigation. These synthetic response checks do not prove server authorization or restoration of permanently deleted events.
- Parent corrected the disappearing close button: inspector body now owns scrolling while title/close remain visible. Final assertions and inspected narrow object/array, dark desktop array and dark mobile403 captures prove the correction.
-18 focused detail/delivery tests92148 and scoped lint11067 pass.

## Delivery limits

No real provider operations or source mutations were made during these browser checks. Historical checks are referenced with their exact bounded scope; final full candidate build, required suites and exact-HEAD release gates remain due. Page/component inventory status is separate from route acceptance.

## Final source interaction acceptance

source-state-actions.cjs98781 passes four320/1440 light/dark cases with custom purple branding and reduced motion. List and detail activation each hold PATCH, disable the switch, retain original state after500, show failure feedback, and retry to the new state. List toggle does not navigate. Graph resubscribe holds POST, disables Cancel, guards Escape, retains its confirmation/error after500 and retries to a refreshed expiry. Parent inspected final light320 and dark1440 error/retry screenshots; actions remain in viewport.15 current Events/EventSourceDetail tests6683 pass. All writes were intercepted. This completes the remaining UI acceptance gaps for the source list/detail routes.
