# Report review checkpoint — 2026-09-08

Both report routes remain In progress. Their earlier rendered evidence is retained in the route ledger.

UsageReports now renders AgentTable for relevant sources while loading and when empty. Previously the page suppressed the whole section unless rows existed. Current synthetic browser usage-agent-current.cjs passes light/dark320x480 and1440x900 loading, true empty, populated long-name rows, source filtering, cached read failure with retained rows, and retry. Parent inspected light320 actual record content and dark320 section composition. Initial script failures were incorrect empty-copy and hidden desktop duplicate selectors, corrected before final41542 terminal0. No real API writes.

Terra implemented ROIReports section-level ListLoadError recovery for trends, workflows and organizations, preserving existing data/calculations/export behavior. Parent reviewed source, formatted files, corrected TypeScript narrowing for trends and typed alert lookup in tests. Current roi-current-recovery.cjs88526 passes four theme/width cases: three simultaneous cold failures do not claim empty data, global retry restores all sections, subsequent cached failure retains workflow/organization records, workflow-only retry does not refetch unrelated sections, and remaining sections recover through the global retry. Parent inspected dark320 cached error/retry composition.

Eight focused tests pass through ./test.sh client unit src/pages/ROIReports.test.tsx src/components/reports/ReportRecordList.test.tsx src/components/reports/formatters.test.ts (56235). Final scoped lint/full TypeScript55437 pass. Earlier TS48271 exposed the narrowing issues now corrected.

Remaining report work: review nested mobile record spacing, all sort columns and CSV contents, populated chart legibility, current agent/storage coverage and demo-source consistency; reconcile with earlier date-filter and permissions evidence. No report route acceptance or global completion is claimed.

## Record layout, sorting and CSV reconciliation

Removed the redundant bordered/padded wrapper around ReportRecordList, retaining the report surface and individual records. Compact metrics use two columns at narrow widths; primary and long fields span both. This shared change covers five Usage and two ROI breakdowns. Parent reviewed actual320px light agent and dark storage/ROI records plus1024px Usage tables.

Agent Input Tokens now sorts by input tokens, matching its column label rather than sorting by input+output. Shared report-csv helper replaces three duplicate serializers and preserves commas, quotes and line breaks in entity names. Existing download filenames, columns and numeric values remain intact. Four focused CSV/record/ROI tests73587 pass; scoped source lint77775 passes.

report-sort-export-current.cjs74227 passes eight light/dark cases at320/768/1024/1440: all five Usage breakdowns, every available sort reversing actual rows, input-only agent ordering with intentionally opposed output counts, all four existing CSV downloads containing correctly escaped labels, mobile/desktop visibility and page bounds. roi-sort-export-current.cjs34581 passes the same eight cases for both ROI breakdowns and exports, with a populated14-point chart. Initial ROI fixture used date instead of the contract period key, corrected; desktop fixture locator excluded hidden regions, corrected after timeout. Final chart check requires two rendered line paths and parent inspected the320px chart with dates and distinguishable solid/dashed series.

Usage demo-source reconciliation is underway in the delegated page-local helper. Parent found and requested corrections to agent CPU and organization execution counts against api/src/routers/usage_reports.py before acceptance. Final full TypeScript and demo browser remain pending. Route count remains54/64.

## Demo and calendar-date review

Terra extracted UsageReports.demo.ts and added agent demo records plus source/org-scoped organization rollups. Parent traced backend semantics and corrected the handoff so agents contribute AI usage without workflow execution counts or CPU/memory totals. Source selection and live API paths remain unchanged. Initial demo browser88875 passes four light/dark320/1440 populated-agent/chart/switch-back-to-real cases; parent inspected the dark320 chart and tooltip.

Parent rendered review found date-only buckets shifted one day west of UTC. Shared axis/tooltip formatters now parse date-only strings as calendar dates; both report demo generators use the same local-date parsing. Unit regression covers exact selected demo dates and full/short chart labels. Twelve report tests57629 pass before the added demo-date regression; final nine focused demo/formatter tests61644 pass. Full TS17261 exposed optional-array typing in delegated tests, corrected; final92241 pending.

Final ROI calendar browser14956 passes four cases: actual period range ends Aug23 without displaying Aug09. The initial Aug10 tick expectation was too strict because narrow charts omit ticks; parent inspected the final320px Aug11/Aug17/Aug23 axis against the Aug10–23 fixture. Both series render. Final Usage demo repeat after generator date correction pending.

Final Usage demo95324 passes four cases after the calendar-date change. Parent source review confirms agents contribute neither execution CPU nor organization execution counts. Three final demo tests35394 pass. TypeScript92241 and97994 sampled the optional trends assertion before its correction; current optional-chain assertion was confirmed on disk and final98225 is running. All browser processes are terminal.

Final scoped lint/full TypeScript98225 passes. Both report routes are UI Verified based on cumulative earlier filter/date-picker evidence and the current all-breakdown layout/sort/export/chart/recovery/demo checks above. Authoritative count56 Verified/8 In progress. Earlier pending entries are chronological; this closes report route acceptance, not global completion.
