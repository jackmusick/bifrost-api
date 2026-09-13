# SDK Provenance, Source Retention, and Update Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Make deployed V2 SDK versions visible, retain the source needed to rebuild them, and let administrators rebuild an app against the current platform SDK without redeploying or reconciling unrelated Solution entities.

**Architecture:** Every source-backed V2 build records immutable SDK provenance on `Application`. Independent deployments retain their sanitized input beside the versioned dist; Solution apps recover their source from the already-retained Solution workspace archive. A shared build/activation service produces a new versioned deployment and atomically advances `active_deployment_id`. A distinct scheduler-owned `application.sdk_update` platform job invokes that service, while REST, CLI, and UI expose derived status and enqueue controls.

**Tech Stack:** FastAPI, SQLAlchemy/Alembic, S3-compatible object storage, PlatformJob scheduler, Click CLI, React Query, React, TypeScript.

---

### Task 1: Persist build provenance and derive SDK status

**Files:**
- Modify: `api/src/models/orm/applications.py`
- Modify: `api/src/models/contracts/applications.py`
- Modify: `api/src/routers/applications.py`
- Add: `api/src/services/application_sdk_status.py`
- Modify: `api/src/services/sdk_package/__init__.py`
- Add: `api/alembic/versions/<revision>_application_sdk_provenance.py`
- Add: `api/tests/unit/test_application_sdk_status.py`
- Modify: `api/tests/unit/test_sdk_package.py`
- Modify: `api/tests/unit/test_applications.py` or the focused application serialization test discovered with `rg`

**Step 1: Write failing status tests**

- Cover `inline_v1 -> not_applicable`.
- Cover V2 with null provenance -> `unknown`.
- Cover V2 with a matching current fingerprint -> `current`.
- Cover V2 with a different/null-old fingerprint -> `update_available` only when build provenance exists.
- Ensure `update_required` is a reserved literal but is not emitted until a minimum supported SDK contract exists.

**Step 2: Run RED**

Run: `./test.sh tests/unit/test_application_sdk_status.py <serialization-test> -v`

**Step 3: Add nullable provenance**

- Add nullable `sdk_package_version: str`, `sdk_fingerprint: str`, `sdk_contract_version: int`, and timezone-aware `sdk_built_at` columns and a reversible migration.
- Add the same raw fields, `sdk_status`, and `sdk_source_available` to `ApplicationPublic`; these are server-owned outputs, not create/update DTO fields or manifest fields.
- Implement a pure status helper accepting app model/provenance and current package metadata. All four provenance fields must be present before reporting `current` or `update_available`.
- Expose one SDK package-version helper used by both tarball stamping and provenance so git-describe versions cannot diverge from the installed npm version.
- Populate the fields in `application_to_public`. Load current metadata off the event loop, degrade a toolchain failure to `unknown`, and compute it once per request rather than once per listed app.

**Step 4: Run GREEN and contract tripwires**

```bash
./test.sh tests/unit/test_application_sdk_status.py <serialization-test> -v
./test.sh tests/unit/test_dto_flags.py tests/unit/test_contract_version.py -v
```

Refresh only the expected CLI contract fingerprint if the additive response fields affect it; do not raise `MIN_CLI_VERSION` for additive outputs.

**Step 5: Commit**

`git commit -m "feat: track deployed app SDK provenance"`

### Task 2: Retain independent V2 source before activation

**Files:**
- Add: `api/src/services/application_source_artifact.py`
- Modify: `api/src/jobs/platform/application_deploy.py`
- Modify: `api/src/routers/applications.py`
- Modify: `api/tests/unit/jobs/test_application_deploy.py`
- Add: `api/tests/unit/test_application_source_artifact.py`

**Step 1: Write failing storage/deploy tests**

- Assert source is copied from transient input to `_application_artifacts/<app-id>/deployments/<deployment-id>/source.zip`.
- Assert retained-source persistence happens after successful compile/upload but before the DB pointer changes.
- Assert retained-source failure leaves the old deployment active and removes incomplete new dist/source.
- Assert successful activation stamps all four SDK provenance fields using the exact package compiled by `SolutionAppBuilder`.
- Assert deleting an independent app removes all retained application artifacts.

**Step 2: Run RED**

`./test.sh tests/unit/jobs/test_application_deploy.py tests/unit/test_application_source_artifact.py -v`

**Step 3: Implement retention**

- Create a dedicated retained artifact abstraction; do not change `ApplicationDeployStorage`'s transient-job contract.
- Copy the already-sanitized CLI upload archive before activation. Store no `node_modules`, `.env*`, build directories, or local credentials; the CLI zip filter remains the first boundary and server zip validation remains the second.
- Keep transient input cleanup in `finally`.
- Delete the new retained source and dist if activation fails. Delete the superseded deployment's source only after successful activation if retention policy is one active deployment.

**Step 4: Run GREEN**

Run the same focused tests and `./test.sh quality api`.

**Step 5: Commit**

`git commit -m "feat: retain independent app deployment source"`

### Task 3: Make Solution V2 deployments versioned and provenance-aware

**Files:**
- Modify: `api/src/services/solutions/deploy.py`
- Modify: `api/src/services/solutions/app_build.py`
- Modify: `api/src/models/orm/applications.py`
- Modify: `api/tests/unit/test_solution_app_deploy.py`
- Modify: `api/tests/unit/test_application_v2_publish_state.py`
- Modify: `api/tests/e2e/platform/test_solution_v2_app_e2e.py`

**Step 1: Write failing tests**

- A source-backed Solution app build gets a fresh deployment UUID, uploads under the versioned dist prefix, and advances `active_deployment_id` only after upload completes.
- It stamps current SDK provenance and `deployed_at`.
- A prebuilt-dist-only install retains null/unknown provenance unless trustworthy package metadata is explicitly present.
- Existing Solution apps with null `active_deployment_id` continue serving legacy unversioned dist until their next build.

**Step 2: Run RED**

Run the focused unit files above via `./test.sh`.

**Step 3: Implement convergence**

- Extend the compiled-app result to carry app ID, deployment ID, dist, and optional SDK metadata.
- Upload source-built Solution app output with `upload_deployment`.
- Do not set the active pointer in the pre-commit entity-upsert phase. After successful artifact upload, atomically update pointer/provenance in a short DB transaction. Preserve the prior pointer on failure.
- Retain the existing read fallback for old unversioned Solution artifacts.

**Step 4: Run GREEN and E2E**

```bash
./test.sh tests/unit/test_solution_app_deploy.py tests/unit/test_application_v2_publish_state.py -v
./test.sh tests/e2e/platform/test_solution_v2_app_e2e.py -v
```

**Step 5: Commit**

`git commit -m "feat: version Solution app deployments"`

### Task 4: Resolve one app's retained source without Solution reconciliation

**Files:**
- Add: `api/src/services/application_source_resolver.py`
- Modify: `api/src/services/solutions/source_artifact.py`
- Add: `api/tests/unit/test_application_source_resolver.py`

**Step 1: Write failing resolver tests**

- Independent app: read active deployment source and return validated app source files/dependencies.
- Solution app: read the owning Solution archive, safely extract it, parse `.bifrost/apps.yaml`, find the manifest app whose `solution_entity_id(solution.id, manifest_id)` equals `Application.id`, and return only its path's source/dependencies.
- Reject traversal paths and symlink escapes.
- Return a typed `source_unavailable` failure for missing legacy artifacts or prebuilt-only source.
- Prove resolution performs no ORM writes and does not call Solution deploy/reconciliation.

**Step 2: Run RED**

`./test.sh tests/unit/test_application_source_resolver.py -v`

**Step 3: Implement the narrow resolver**

- Reuse the established safe zip extraction and app skip rules; extract shared helpers rather than duplicating them.
- Keep source reads private/admin-only at the router boundary; this service returns build input only.

**Step 4: Run GREEN**

Run the focused test and affected zip-install/solution tests.

**Step 5: Commit**

`git commit -m "feat: resolve retained source for app rebuilds"`

### Task 5: Add the `application.sdk_update` platform job

**Files:**
- Add: `api/src/jobs/platform/application_sdk_update.py`
- Modify: `api/src/jobs/platform/application_deploy.py`
- Add or modify: `api/src/services/application_build.py`
- Modify: `api/src/jobs/platform/registry.py`
- Add: `api/tests/unit/jobs/test_application_sdk_update.py`
- Modify: platform-job registry/policy tests discovered with `rg`

**Step 1: Write failing job tests**

- Registered definition has type `application.sdk_update`, payload version 1, a 20-minute timeout, one attempt, and `min_memory_headroom_mb=512`.
- It resolves retained source, compiles with the current SDK, uploads a fresh versioned dist, persists source for the new independent deployment where applicable, and atomically activates/stamps provenance.
- Build/upload/source failures preserve the prior active deployment and metadata and clean incomplete artifacts.
- It never modifies app source, manifests, Git state, or unrelated Solution entities.

**Step 2: Run RED**

`./test.sh tests/unit/jobs/test_application_sdk_update.py <registry-test> -v`

**Step 3: Extract and reuse build primitives**

- Move compile/upload/activate/stamp/cleanup into a shared application-build service used by both `application.deploy` and `application.sdk_update`; do not duplicate the build pipeline.
- Payload contains application ID and expected active deployment/provenance for stale-request protection.
- Keep the job scheduler-owned; add no feature worker, job table, job status endpoint, or polling loop.

**Step 4: Run GREEN**

Run focused job tests plus existing `test_application_deploy.py` and `./test.sh quality api`.

**Step 5: Commit**

`git commit -m "feat: rebuild apps with the current SDK"`

### Task 6: Expose status, source export, and update enqueue APIs

**Files:**
- Modify: `api/src/models/contracts/applications.py`
- Modify: `api/src/routers/applications.py`
- Modify: `api/src/routers/solutions.py`
- Add: `api/tests/e2e/platform/test_application_sdk_update.py`
- Modify: `api/tests/e2e/platform/test_solution_v2_app_e2e.py`

**Step 1: Write failing endpoint tests**

- App list/get exposes provenance, derived status, and source availability.
- Admin can download retained source for an independent V2 app; non-admin and unavailable-source cases fail safely.
- `POST /api/applications/{id}/sdk/update` enqueues/reuses a shared platform job with `resource_lock_key=application:<id>`, notification, Location header, and `PlatformJobAccepted`.
- Batch enqueue includes only V2 apps with available source and non-current/unknown provenance, reports per-app accepted/skipped results, and does not build synchronously.
- Solution status aggregates contained apps. Solution update enqueues one app job per actionable contained app without invoking full Solution deploy.

**Step 2: Run RED**

Run the two focused E2E files.

**Step 3: Implement thin endpoints**

- Use Pydantic request/response models from the contracts package.
- Reuse `enqueue_platform_job`, shared notification transport, and shared platform-job status route.
- Use the same app resource lock for deploy and SDK update. For Solution-owned apps, also prevent overlap with a Solution deploy through the existing Solution write lock or an explicit compatible lock check.
- Do not add browser polling.

**Step 4: Run GREEN and regenerate types**

```bash
./test.sh tests/e2e/platform/test_application_sdk_update.py tests/e2e/platform/test_solution_v2_app_e2e.py -v
./debug.sh status | grep -q "Status:   UP" || ./debug.sh up
(cd client && npm run generate:types)
```

**Step 5: Commit**

`git commit -m "feat: expose app SDK update operations"`

### Task 7: Add CLI status, export/update, and batch orchestration

**Files:**
- Modify: `api/bifrost/commands/apps.py`
- Modify: `api/bifrost/commands/app.py`
- Modify: `api/bifrost/commands/solution.py`
- Modify: `api/tests/unit/test_cli_apps.py`
- Modify: `api/tests/unit/test_cli_app.py`
- Modify: `api/tests/unit/test_solution_start_sdk_warning.py`

**Step 1: Write failing CLI tests**

- `bifrost apps sdk status [ref]` prints deployed provenance/status/source availability.
- `bifrost apps sdk update <ref>` and `--all` enqueue remote platform jobs and poll `/api/platform-jobs/{id}` with short requests until terminal status.
- Add an independent app source-download/export command that writes the retained zip without overwriting a non-empty destination.
- Preserve existing `bifrost solution sdk update` as the local workspace re-vendor command; add explicit deployed-status/update subcommands or flags with unambiguous help rather than silently changing its meaning.
- A batch reports skipped unavailable/inline/current apps and exits nonzero only for actual failed jobs.

**Step 2: Run RED**

Run the three focused CLI unit files.

**Step 3: Implement commands**

- Reuse one generic platform-job polling helper instead of copying publish/deploy loops.
- Resolve app/Solution refs through `RefResolver`.
- Keep local source update separate from deployed artifact rebuild.

**Step 4: Run GREEN and CLI contract checks**

```bash
./test.sh tests/unit/test_cli_apps.py tests/unit/test_cli_app.py tests/unit/test_solution_start_sdk_warning.py -v
./test.sh tests/unit/test_contract_version.py tests/unit/test_skill_truth.py -v
```

Regenerate skill appendices if command help changes.

**Step 5: Commit**

`git commit -m "feat: manage app SDK updates from the CLI"`

### Task 8: Add application and Solution badges/actions

**Files:**
- Modify: `client/src/hooks/useApplications.ts`
- Modify: `client/src/components/applications/ApplicationListSurface.tsx`
- Modify: `client/src/pages/Applications.tsx`
- Modify: `client/src/pages/Applications.test.tsx`
- Modify: `client/src/services/solutions.ts`
- Modify: `client/src/pages/Solutions.tsx`
- Modify: `client/src/pages/Solutions.test.tsx`
- Modify: `client/src/pages/SolutionDetail.tsx`
- Modify: `client/src/pages/SolutionDetail.test.tsx`

**Step 1: Write failing component tests**

- V2 `update_available` and `unknown` apps display an “SDK update available”/“SDK version unknown” badge; V1/current apps do not.
- Admin action queues an in-place SDK update and explains that source is rebuilt without a full Solution deploy.
- Action is disabled with an explicit reason when source is unavailable.
- Solution list/detail aggregate statuses and offer update-all while keeping existing Git update badges distinct.
- Success points users to notification progress; no feature polling is introduced.

**Step 2: Run RED**

Run targeted Vitest files through `./test.sh client unit`.

**Step 3: Implement UI**

- Add React Query mutations in existing hooks/services and invalidate app/Solution queries on enqueue/terminal notification refresh.
- Put compact badges in both grid and table layouts and a menu action in existing action menus.
- Keep Solution-managed source/settings restrictions intact; SDK rebuild is the one explicitly allowed app operation.

**Step 4: Run GREEN and static checks**

```bash
./test.sh client unit src/pages/Applications.test.tsx src/pages/Solutions.test.tsx src/pages/SolutionDetail.test.tsx
(cd client && npm run tsc && npm run lint)
```

**Step 5: Commit**

`git commit -m "feat: show and update deployed app SDKs"`

### Task 9: Document the source/SDK contract and benchmark build memory

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Add: `docs/runbooks/application-sdk-update.md`
- Modify: relevant docs tests if present

**Step 1: Add identical agent guidance**

- Document `client/src/lib/app-sdk` as SDK source of truth, build-time injection, provenance stamping, source exclusions, contract-version rules, retained-source privacy, and the rule that SDK-only rebuilds never reconcile Solutions or mutate Git/manifests.
- Keep the new section byte-identical in `AGENTS.md` and `CLAUDE.md`.

**Step 2: Benchmark through the scheduler**

- Run representative small and dependency-heavy app SDK-update jobs in the debug stack.
- Record wall time plus start/peak cgroup working set from existing platform-job memory diagnostics.
- Keep `min_memory_headroom_mb=512` unless measurements justify a tested change. Record observed numbers rather than the earlier ~200 MB recollection.

**Step 3: Verify docs and behavior**

Run relevant documentation/agent-file parity tests plus all focused backend/client tests from prior tasks.

**Step 4: Commit**

`git commit -m "docs: define app SDK update lifecycle"`

### Task 10: Complete end-to-end verification

**Step 1: Exercise the happy path**

- Deploy an independent V2 app, confirm stored source/provenance/current status.
- Change the platform SDK fingerprint, confirm update-available status.
- Enqueue in-place update, follow the shared notification/platform-job state, confirm a new deployment pointer and current status with unchanged application source.
- Repeat for one Solution-owned source-backed app and confirm no other Solution entity changes.

**Step 2: Run scoped quality and tests**

Run all affected unit/E2E files, `./test.sh quality api`, client `tsc`/`lint`, DTO parity, contract version, and skill-truth checks.

**Step 3: Run the required clean-candidate gate**

- Ensure the worktree is clean and rebased/merged onto current `origin/main`.
- Record candidate SHA.
- Run `./test.sh pre-pr` against that exact commit.
- Any failure requires a durable disposition and a new candidate commit followed by another full pre-PR run.
