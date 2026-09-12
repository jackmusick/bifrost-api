# V1 Inline App Compatibility

This note captures the current public contract for V1 inline apps while the design-system migration is in progress.

## Runtime surface

V1 apps still import from `bifrost`, which is the host-loaded public package surface defined in [`client/src/lib/bifrost-runtime.ts`](../../client/src/lib/bifrost-runtime.ts).

The surface currently includes:

- React primitives
- The shared `react-router-dom` set
- Lucide icons
- Platform hooks and helpers such as `useWorkflowQuery`, `useWorkflowMutation`, `useLocation`, `useParams`, `useSearchParams`, `navigate`, `useNavigate`, `useUser`, `RequireRole`, `useAppState`, `Link`, `NavLink`, and `Navigate`
- SDK helpers such as `tables`, `useTable`, `useInfiniteTable`, `files`, and `useFiles`
- Utility exports such as `clsx`, `twMerge`, `format`, and `utils`
- The shadcn UI component set, including `Badge`, `Table`, `Command`, `Sheet`, `Dialog`, `Card`, `Button`, `Tabs`, `Popover`, `Tooltip`, `Select`, `DateRangePicker`, `CalendarPicker`, and related subcomponents

The injected app-code scope in [`client/src/lib/app-code-runtime.ts`](../../client/src/lib/app-code-runtime.ts) mirrors that surface and is what compiled V1 code actually receives at runtime.

## Contract details that matter for migration

- `Link`, `NavLink`, `Navigate`, and `useNavigate` are app-base-path aware wrappers. They must continue transforming absolute paths against the app shell base path.
- `useLocation` must continue returning app-relative pathnames.
- `BundledAppShell` renders the inline V1 bundle in the host React tree, so V1 apps inherit host providers and host CSS.
- The shell also applies org scope to table access and app context for navigation transforms.

## Current risk areas

- Styling is not isolated. Any change to the shared design system, token names, or global selectors affects inline V1 apps immediately.
- Several components depend on selector-heavy Tailwind contracts such as `data-slot`, `group/*`, `has-*`, and `@container`.
- `CommandDialog` is a compatibility wrapper, not a plain `Dialog`. It must keep auto-wrapping `CommandInput` / `CommandList` children in `Command`.
- `CalendarPicker` is the date picker export; `Calendar` from `bifrost` remains the Lucide icon.
- `Button` still needs to forward native props and `asChild` behavior correctly because V1 apps use it as a generic interactive primitive.

## Legacy components fixture

The synthetic fixture lives under
`docs/design-modernization/fixtures/legacy-components/` and seeds a real inline
v1 app named `Design Review Legacy Components`.

- Preview route: `/apps/design-review-legacy-components/preview`
- Live route: `/apps/design-review-legacy-components`
- Source file: `fixtures/legacy-components/pages/index.tsx`
- Command note: `fixtures/legacy-components/commands.md`

The app intentionally imports the published `bifrost` aliases for
`Button`/`asChild`, `Card`, `Input`, `Select`, `Dialog`, `CommandDialog`,
`Tabs`, and `CalendarPicker` so the compatibility contract stays visible in one
contained route.

## What is covered by tests now

- Runtime export drift between the client `$` registry and Python platform names is pinned in [`api/tests/unit/test_platform_names_match_runtime.py`](../../api/tests/unit/test_platform_names_match_runtime.py).
- V1 import classification and bundler handling are pinned in the compiler and validator tests under `api/tests/unit/`.
- The new focused component test covers the public contract that is most likely to break during a visual migration:
  - `Button` native props and ref forwarding
  - `Button asChild` ref forwarding
  - `CommandDialog` auto-wrapper behavior
  - `CalendarPicker` aliasing versus the Lucide `Calendar` icon

## Current source audit (2026-09-07)

The parent confirmed that the export registries in `app-code-platform/components.ts`
and `bifrost-runtime.ts` have no diff against baseline `0598020e3`. The retained
components still resolve through the host UI library. This proves export-name
continuity; it does not by itself prove every underlying component prop or
behavior remains compatible.

The four focused compatibility tests cover native/ref and `asChild` Button
behavior, the CommandDialog wrapper, and CalendarPicker/icon alias separation.
The real legacy fixture additionally exercises preview and published routing,
Dialog, CommandDialog search, controlled form inputs, Select, tabs and calendar
layout. Broader compiler/export drift gates and final candidate verification
remain part of release acceptance.

## Generated CSS precedence

Legacy compiler utilities use the `bifrost-app-utilities` cascade layer, ordered below host components/utilities. They add classes absent from the host without overriding its responsive layout. Authored app CSS stays unlayered; shared React providers and body-portaled controls remain unchanged. Bundle schema4 refreshes old generated assets through the existing manifest rebuild path for both draft and live inline apps. This does not sandbox arbitrary authored global CSS or alter standalone V2 asset ownership.

V1 matrix4230 passed all eight published/preview x320/1440 light/dark custom-purple reduced-motion cases after the utility-layer correction. It exercises metadata failure/retry, Dialog, CommandDialog search, Select, controlled input, tabs and calendar width. Parent inspected the dark320 preview capture; the fixture page itself scrolls and the calendar continues below the captured viewport. This is component/route behavior evidence, not a new full app-editor acceptance. API quality25767 completed successfully: Pyright reports0 errors/0 warnings and Ruff reports all checks passed.

## Production-source compatibility exercise (2026-09-08)

A read-only copy of production's **Service Margin Dashboard** is published in the
review debug stack as `/apps/v1-review-margin-dashboard` (application
`268e5b3a-5373-46c5-a76c-0a4139b42d4f`). Its ten source files, including the layout,
five pages, three local components and `app.yaml`, were verified byte for byte
against the production download. Its Recharts 3.7 dependency is retained.
Production source is not checked into this repository.

Ten debug-only workflows implement the original path/function references with
synthetic clients, financial metrics and team members. Refresh and analysis return
synthetic results; they do not call production integrations or an AI provider.
Pool changes persist to `v1-review-margin-pools.json` in the debug temp file
location. Its file policy allows platform-admin read/write, matching the review
account. No production records, credentials or role assignments were copied.

Browser acceptance on the published copy:

- All five routes loaded: summary, team, clients, actions and pools.
- Summary Recharts bars, gauge sectors and trend line rendered after animation.
- Client search filtered rows; opening a row loaded the detail Sheet; Escape closed it.
- Re-analyze and Refresh Data completed against the synthetic workflows.
- Dragging an unassigned member into Projects persisted across reload; removing
  the member persisted and restored the initial assignment.
- Desktop dark and light summary captures were taken. The parent inspected the
  dark summary and detail Sheet. Route and client interaction checks reported no
  browser page errors.

This exercise also exposed limitations already explicit in the copied source:
its fixed `w-64` sidebar squeezes the content at 390px, and its Sheet specifies a
400px minimum width. The mobile client-page capture confirms the sidebar issue.
The source is deliberately unchanged; this is a compatibility fixture, not a
redesign of the copied app. These app-authored layouts require their own mobile
adaptation. A zero document overflow measurement alone did not catch the visibly
cramped content.

The current branch also passed 43 tests across runtime exports, app shells,
workflow hooks, routing and the focused compatibility fixture, plus the eight
published/preview × 320/1440 × light/dark browser cases for the synthetic legacy
components app. These are evidence for the exercised contracts, not certification
of every V1 component, every production app or visual equivalence to the old host.
Shared V1 components continue to inherit the host design; app-authored layouts and
colors remain in the app source.
