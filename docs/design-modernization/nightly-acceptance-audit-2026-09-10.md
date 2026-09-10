# Nightly acceptance audit — 2026-09-10

Candidate: `f8cd43a8c66dbb259c497efc2c22c62fb0df9560`, clean throughout the run.

Command: `./test.sh client nightly --workers=2`

Result: **105 passed, 22 failed, 1 skipped, 0 flaky**, 128 selected cases,
592.9 seconds. This is a failed gate, not launch approval. The skipped case
is included below and requires resolution; it is not counted as accepted.
The complete HTML/JSON, first-failure screenshots, videos and traces were
retained locally under `/tmp/bifrost-nightly-f8cd43a8c-evidence/` before any
subsequent test run. These local artifacts are not committed to Git.

All rows below remain owned repair work until the exposing conditions pass.
Source review distinguishes obsolete selectors from product layout and fixture
isolation problems; a successful isolated rerun alone does not close a
concurrency or order-dependent failure.

| Spec | Case | Project | Observed status |
| --- | --- | --- | --- |
| `agents-detail-runs.admin.spec.ts` | groups run activity, expands delegated traces, and reserves raw data for Advanced | platform-admin | failed |
| `agents-detail-runs.admin.spec.ts` | keeps Overview context fixed and View all runs navigates | platform-admin | failed |
| `agents-detail-runs.admin.spec.ts` | keeps run context fixed on desktop and falls back to page scrolling | platform-admin | failed |
| `apps-publish-notification.admin.spec.ts` | queues in the dialog and reports completion through notifications | platform-admin | timedOut |
| `chat-attachments.admin.spec.ts` | browses the persistent artifact library | platform-admin | failed |
| `desktop-scroll.admin.spec.ts` | document records accept wheel scrolling at 1100px, filters true | platform-admin | failed |
| `entity-logos.admin.spec.ts` | uploads via the app settings dialog and renders on the card | platform-admin | failed |
| `entity-logos.admin.spec.ts` | uploads via the drop zone and renders on the fleet card | platform-admin | timedOut |
| `event-source-graph.admin.spec.ts` | shows Graph context and recreates the provider subscription | platform-admin | failed |
| `memory.admin.spec.ts` | enables and manages private memory | platform-admin | failed |
| `per-mapping-oauth.admin.spec.ts` | mapping table renders on integration detail page | platform-admin | failed |
| `per-mapping-oauth.admin.spec.ts` | Connect button on mapping row opens authorize URL | platform-admin | skipped |
| `policy-rules-manager.admin.spec.ts` | open manager, create rule, edit, see built-in badge, attempt in-use delete | platform-admin | timedOut |
| `policy-rules-reference.admin.spec.ts` | Files policy editor shows the rule in Insert reference dropdown | platform-admin | timedOut |
| `policy-rules-reference.admin.spec.ts` | Tables policy editor shows the rule in Insert reference dropdown | platform-admin | timedOut |
| `roles.detail.admin.spec.ts` | card → users chip → drawer → assigned → unassign | platform-admin | failed |
| `scheduler-diagnostics.admin.spec.ts` | shows capacity guidance and opens per-run logs | platform-admin | failed |
| `solution-backup-export.admin.spec.ts` | queues a scheduler-owned backup export and downloads it when completed | platform-admin | failed |
| `solution-files-link.admin.spec.ts` | Files chip appears in Contents and opens the embedded file browser | platform-admin | failed |
| `users.admin.spec.ts` | admin invites user and user registers via magic link | platform-admin | timedOut |
| `agents-owner-budget-hidden.user.spec.ts` | budget fields are not visible to non-admin users | org-user | timedOut |
| `forms.user.spec.ts` | [FORM-ACCESS-01 desktop] member cannot see or open an unassigned role-based form | org-user | failed |
| `scheduled-execution.spec.ts` | schedule a run from the workflow execute page | chromium | timedOut |

## Initial diagnosis and repair grouping

- Notification completion rendered correctly; the publish test searched the
  title wrapper instead of its named notification article.
- Graph events and scheduler schedules retain desktop/mobile representations;
  broad text selectors matched both. Use visible semantic links/rows.
- Role pagination now uses the shared `List pagination` navigation. Preserve
  assignment/unassignment behavior while asserting the current footer.
- Backup export's `Config values` substring also matched the secret-values
  checkbox. Match the intended label rather than another field's description.
- Agent Overview uses the common bounded Page content region. Its old test
  assumes a separate inner Recent activity scroller. Filter overflow at short
  desktop heights still needs functional verification and potential repair.
- The artifact touch-target measurement was taken during a layout transition;
  assert settled geometry with a condition, not a fixed sleep or looser target.
- Memory setup uses an obsolete embedding-config payload and outdated settings
  routes. Repair fixture setup and retain real memory persistence proof.
- Form-access setup failed with `Workflow already registered` under the full
  suite. Resolve workflow registration/discovery ownership before closing it.
- Remaining logo, policy editor, solution file browser, invitation and schedule
  failures need source/trace diagnosis. They are not dismissed as unrelated.

A separate explicit compilation of all `client/e2e/**/*.ts` found nine errors
in three files (docs seeders' APIResponse type, scheduled-execution's Page import,
and the V2 runtime fixture's window declaration). The repair is separate from
browser outcomes; normal source-only client compilation had not covered them.

## First verified repair subset

The following targeted run passed all seven selected tests (including setup)
with two workers, zero retries, zero skips, and zero failures:

```sh
./test.sh client e2e e2e/apps-publish-notification.admin.spec.ts e2e/event-source-graph.admin.spec.ts e2e/scheduler-diagnostics.admin.spec.ts e2e/solution-backup-export.admin.spec.ts e2e/roles.detail.admin.spec.ts --workers=2
```

This verifies the five selector/footer repairs while preserving real publish,
assignment/unassignment, scheduler inspection, and backup export/download
outcomes. Graph provider traffic remains intercepted by its existing test.
Explicit TypeScript compilation of every `client/e2e/**/*.ts` now passes after
the three type fixes; ESLint passed for all eight modified browser/helper files.
These are targeted iteration results. All remaining failures are still owned,
and the full nightly must pass again on the final clean candidate.
