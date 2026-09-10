# Connected review fixtures and frontend confidence

## Current inventory

Read from the isolated design-review debug API on 2026-09-09:

| Resource | Count |
| --- | ---: |
| Integrations | 6 |
| Event sources | 0 |
| Agents | 2 |
| Forms | 17 |
| Apps | 3 |
| Workflows | 83 |

Counts are not a coverage measure: some records are duplicates or imported
compatibility examples. They do not guarantee useful dependencies, event
history, permissions, or executable paths.

## Proposed fixture pack

Create an idempotent seeder with a clearly named review namespace. Preserve
existing review resources. Reuse the current synthetic streaming/success/failure
workflow source and regular platform APIs.

1. Two organizations and platform/admin/member accounts with known role access.
2. Integration configuration, global and organization mappings, and an entity
   provider backed by synthetic local data.
3. A local webhook source and subscriptions to synthetic workflows. Submit real
   local events so event details, deliveries, failure, and retry have actual
   records. Include a disabled source; avoid recurring traffic by default.
4. Agents with tools, conversation history, and representative outcomes; forms
   that execute the same workflows; apps with uploaded logos and published/draft
   examples. Retain the imported V1 compatibility examples separately.
5. Enough records to exercise search and a second pagination page, plus long
   labels and missing optional descriptions/artwork.
6. A review index listing each page, fixture, primary action, expected result,
   and whether the path was checked as admin and member.

A useful connected pack is a moderate bounded implementation task. Simply
adding list records is smaller; remote OAuth consent, external adapters, email
and other real integrations require separate acceptance conditions. Do not fake
live connection health. Existing documentation seeders include no-op and
best-effort implementations and should not be treated as this fixture pack.

## Test inventory and gaps

The repository currently contains 478 `client/src` test files and 56 browser
spec files. These are file counts, not a coverage percentage or a claim that
all tests passed. Component tests exercise isolated behavior, frequently with
mocked hooks. Browser specs exercise selected journeys against live services.
Neither proves every menu item and interaction works.

Before launch, use the seeded review index as an interaction matrix: create,
edit, save, cancel, delete, open, search/filter, paginate, execute/retry, and
scope changes where relevant. Cover shared control edge cases in component
tests; cover each important connected journey in browser tests. Include
signed-out, insufficient-role, active execution, and request-failure recovery.
Run the repository's full pre-PR gate after scoped checks and final visual
acceptance; it has not been run for this iteration.

## Changes delivered in this iteration

- Integrations cards have explicit Select/Done mode. In selection mode the
  card is the keyboard/click target, selection is visible, and nested navigation
  and menus are removed. Normal mode opens the item and has no checkbox.
- PageShell and ProtectedRoute wait for sign-in recovery when unauthenticated;
  role denial is reserved for authenticated users.
- A resource 401 checks `/auth/me` before refreshing or clearing the session.
  A valid identity, identity service failure, and normal 403 stay with the page.
  Confirmed invalid identity follows refresh/recovery. Embed capability and
  login endpoint failures stay with their own callers.
- Access copy reads “You don’t have access”; the home action is named correctly.

Scoped verification: shared API auth tests (21), access component tests (12),
audit page tests (3), Integrations page tests (5); production browser journeys
for card selection and signed-out redirect passed, including setup (3 tests).
Mobile/desktop selection layouts were visually reviewed. Full suites are not
claimed by this result.
