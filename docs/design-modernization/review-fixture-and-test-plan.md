# Connected review fixtures and frontend confidence

For the source-audited page/capability backlog, assertion standards, delivery batches, and coverage ledger, see [UI acceptance coverage](ui-acceptance-plan.md). This note describes the delivered connected review fixture, how to refresh its local debug index, and what it proves today.

## Delivered review pack

The current implementation is split across three files:

- `scripts/seed-review-pack.py` is the debug-stack wrapper. It reads the running debug URL and login from `./debug.sh status`, passes credentials through stdin to the TypeScript runner, and prints only a non-secret JSON index.
- `client/e2e/fixtures/review-pack.ts` owns the idempotent fixture API. It derives all names from `--namespace`, creates or reuses the namespace resources, returns links and expected markers, and exposes cleanup for isolated browser tests.
- `client/e2e/support/seed-review-pack.ts` is the persistent debug companion. It signs into the debug stack, calls `ensureReviewPack`, verifies a second ensure returns the same IDs, and optionally executes the owned form/webhook review path while writing screenshots and a failure summary under the requested artifacts directory.

The fixture intentionally uses synthetic local platform data. It creates one namespace-specific organization, one integration and organization mapping, two Python workflows, one generic webhook source with one workflow subscription, one form, one deterministic agent record, and one Home collection containing the form and agent. It does not claim external provider health, remote OAuth consent, email delivery, third-party webhook compatibility, or production connector availability.

Generate the current debug index with:

```bash
scripts/seed-review-pack.py --namespace design-review --artifacts /tmp/bifrost-debug-review-artifacts > /tmp/bifrost-debug-review-index.json
```

Use the generated `/tmp/bifrost-debug-review-index.json` for exact local links and IDs during review. Do not copy those IDs into repository docs; they are debug-stack state.

## Cleanup and retention behavior

The isolated browser spec uses a unique namespace and calls the fixture cleanup in `finally`, deleting only resources whose names are derived from that namespace. Cleanup covers the Home collection, event source, form, agent, integration, organization, and the two workflow source files. It does not delete unrelated resources or legacy Covi Portal review examples.

The debug wrapper passes `cleanupOnFailure: false`. That is deliberate: if a connected review run fails, the owned namespace remains in the debug stack so the reviewer can inspect the exact resources, Home entries, form execution, webhook event, deliveries, and execution results. Re-running the same namespace is idempotent and should retain stable resource identities unless a reviewer manually deletes one of the owned records.

## Acceptance proof currently available

`client/e2e/review-pack-acceptance.admin.spec.ts` now provides the checked-in browser acceptance path for the isolated review pack. It creates an `acceptance-*` namespace, calls `ensureReviewPack` twice, asserts stable IDs, asserts exactly one owned subscription and one owned Home collection, launches the seeded form from Home, submits it, verifies the execution result marker and integration mapping entity, sends the generic webhook, waits for successful delivery, opens the event source Events tab, verifies the completed event and delivery, opens the linked execution, and verifies the webhook result marker and mapping entity.

Parent reports this review-pack acceptance journey is passing. Parent also successfully seeded the persistent `design-review` namespace and completed the debug form execution plus webhook delivery. The latest screenshot/Home checkpoint still has a pending selector fix for a mobile-hidden sidebar condition, so this README does not claim final visual/mobile Home acceptance from the debug helper.

## What this does not deliver

The old proposed fixture pack described two organizations, dedicated role/account matrices, pagination padding, disabled sources, broad agent history, imported compatibility examples, and larger cross-route data volume. Those are not delivered by this helper. The global browser setup and other fixtures already provide two-org/role/account coverage where their specs need it; this debug helper stays focused on one connected Home/form/webhook/integration chain.

Existing Covi Portal review resources are unchanged and should be reviewed separately. They are useful compatibility data, but they are not owned by this helper and are not cleaned up by it.

## Current milestone and remaining limits

The current milestone is a connected, idempotent, locally seeded review chain that proves the platform can create reusable review resources, expose them through Home, execute a seeded form workflow, deliver a local generic webhook to a workflow, and inspect the resulting event and execution records. It is suitable for targeted manual review and for the passing isolated browser spec.

Remaining manual limits are finite: inspect responsive Home screenshots after the mobile-hidden selector fix, review existing Covi Portal examples separately, and rely on the main/nightly/pre-PR gates before making release-wide claims. Do not treat the generated index, the debug helper, or this spec as evidence for external provider health or every proposed backlog item.

## Latest debug exercise

The persistent `design-review` form and webhook were exercised successfully through the public debug URL on 2026-09-10. The generated index includes both execution links. Home and result-first execution screenshots were reviewed at 1440px and 390px; the compact header now stays on one toolbar row. Artifacts: `/tmp/bifrost-connected-review-visuals/`, index: `/tmp/bifrost-debug-review-exercised.json`. The earlier Home checkpoint selected the hidden mobile sidebar label; the runner now scopes the collection assertion to the visible Collections region. These are debug iteration observations, not clean-candidate test-gate results.
