# Covi Portal V1 compatibility review

The debug app `/apps/v1-review-covi-portal` copies the current workspace source of
production Covi Portal V1 (`64f2065e-a16e-4e40-a374-fc36ebb7a49c`, source prefix
`apps/covi-portal`). Production was read-only. This is not a V2 conversion and
not a change to the separate production Covi Portal V2 application.

Production reports unpublished changes. This fixture therefore represents the
current V1 source, not a verified byte-for-byte reconstruction of the August 6
published snapshot.

## Copy boundary

The 57 source files include the existing layout, styles, local component library,
hooks and pages. Thirty-seven files are byte-for-byte unchanged. Twenty contain
only substitutions of workflow references for debug-only `path::function`
references. Layouts, CSS, component APIs and dependency declarations are retained.
Production frontend source is kept outside this public platform repository.

Covi Portal owns its DM Sans typography, `--cv-*` tokens and many local controls.
Those remain app-owned. Host exports, hooks and any imported host controls still
come from the Bifrost V1 runtime; this is not CSS or JavaScript isolation.

## Synthetic dependencies

Debug-only workflows cover dashboard, organization selection, permissions,
employees and lifecycle, tickets, assets, backups, mail and site onboarding.
They use fictional people, example.com email addresses and demo equipment.
Production integration configuration, credentials and customer data are not copied.
No fixture calls Microsoft Graph, Exchange, HaloPSA or backup services.

Action fixtures simulate results. A successful ticket, mail or account action is
not evidence that a real external operation occurred. Stateless action fixtures
need not persist after reload; lifecycle table backing is documented with the
acceptance results below.

## Findings and acceptance

The first publish exposed a host runtime defect: the Python bundler export list
omitted `createContext` and `createElement`. The synthesizer misclassified these
React primitives as Lucide imports, preventing Portal's authentication context
from loading. The host export list now includes the public React surface, the
client public module also exports `createElement`, and the drift test derives
React names from that module rather than skipping a second hardcoded list.
Bundle schema 5 rebuilds cached bundles through the existing schema mechanism.

The copied app rebuilt successfully after this correction. The route pass covered
18 routes: dashboard; employee list/detail/onboard/offboard/reactivate/history and
both mailbox-access pages; ticket list/detail/new; assets; backups; shared mail,
M365 groups and distribution lists; site onboarding. Browser page-error capture
was empty. An initial employee-list screenshot was taken before rendering
completed; a subsequent condition-based check verified populated employee rows.

Parent acceptance also verified:

- Populated employee detail and employee list.
- Mail permission dialog opened with populated permissions and closed.
- Ticket composition returned the synthetic success state, without sending to Halo.
- Dark desktop dashboard, onboarding form and mail dialog inspected visually;
  light desktop and three mobile captures taken.
- Returning to Apps through the host Back button restored the body's font and
  background overrides and removed app CSS links.
- Backend export/bundler tests: 18 passed, including Portal React import regression.
- API Pyright/Ruff: passed, zero errors/warnings. Client TypeScript: passed.

The three Provider-scoped debug tables are `onboarding_runs`, `offboarding_runs`
and `portal_user_changes`. Completed fixed-ID onboarding/reactivation/offboarding
rows and five employee audit rows were seeded and queried. They support the
fixture's fixed lifecycle IDs; a full live lifecycle submission and every
mutation path were not browser-certified. Fixtures simulate results and are not
production integration or customer-role authorization tests.

**Mobile limitation:** the copied Portal CSS retains a fixed 244px sidebar and
its main content retains 36px horizontal padding. At 390px, the main column is
only 146px wide; the dashboard title collapses to zero width alongside its
unwrapped actions. The screenshots confirm unusably cramped content. This
constraint is explicit in the unchanged Portal source. It is preserved for a
faithful compatibility review and requires a separate Portal mobile redesign.

The evidence supports desktop compatibility for the exercised surfaces after the
host fix. It does not establish visual equivalence to the published production
snapshot, complete mobile usability, or acceptance of every V1 control and role.

The existing legacy-components browser matrix also passed all eight
published/preview × 320/1440 × light/dark cases after the schema 5 change,
covering loader/error retry, reduced motion, Dialog, CommandDialog, controlled
input, Select, tabs and calendar layout.

## Current debug fixture recheck — 2026-09-10

Read-only browser review on the current source-mounted debug stack loaded the real sanitized V1 Portal fixture. Dashboard asserted the fictional ticket `Demo laptop docking issue`; Tickets, Assets and Backups asserted their known fictional ticket/device content. All four populated screens loaded with zero JavaScript page errors. Screenshots remain private under `/tmp/bifrost-final-v1-review/portal-*.png`; no production source or credentials were committed. Parent reviewed populated dashboard and 390px Backups. The inherited fixed 244px sidebar still leaves the mobile content unusably narrow. This is an existing app-owned layout limitation, not a claim of Portal mobile acceptance or every Portal action passing. Earlier transient blank login observations were followed by instrumented successful navigation; no code repair is attributed to those observations.
