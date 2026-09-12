# Remaining modernization work

Current checkpoint: all64 route entries are UI Verified. This includes Layout and ContentLayout; see shell-review.md. The chronology in PROGRESS.md and individual review notes preserves older counts and superseded findings.

## Shared contract reconciliation

- Foundation, branding and V1 UI contracts are consolidated in shared-contract-review.md; all14 family rows are reconciled. Final candidate API/compiler gates remain due.
- All151 page modules,53 primitives and374 feature components are UI Verified. Retained compatibility ownership and final repairs are documented in retained-component-review.md and asset-reconciliation.md.
- Shared toast/modal stacking is fixed and rendered. Consistent record actions are documented in list-action-audit.md, including the later integration-mapping correction in PROGRESS.md.

## Validation and delivery

- Full client lint and production build pass on the current working source. Final TypeScript23848 and scoped lint pass after the retained component repairs.
- First full Vitest run:452/453 files and2689/2690 tests pass. Events had an unfrozen relative-date assertion. Date-only clock and cleanup fix it; all6 focused Events tests76454 pass. Full-suite confirmation passes453 files /2690 tests (client-full-unit-fixed.log).
- Parent diff/contract reconciliation completed. Current origin/main equals the migration baseline0598020e3; no merge is needed. Targeted API/compiler boundary run20160 passes21 tests (worktree JUnit:21 tests,0 failures/errors).
- Commit the exact candidate and pass ./test.sh pre-pr on a clean, current-main HEAD. Repair any discovered failures; no waived failures or retry-until-green.
- Verify the built candidate through the NetBird preview, complete authorized push/delivery, and report exact SHA/check results.

The preview remains http://bifrost-debug-design-system-modernization-0-38.netbird.cloud. Browser recovery tests use synthetic API/WebSocket fixtures; they do not create real workflow executions or identity-provider changes.

## Latest gate checkpoint

Initial committed-candidate gate passed all2699 client tests, backend quality,5938 unit tests and1808 backend E2E tests, then found ambiguous public-form browser locators after accessible copy/status additions. The complete corrected public-form spec passes5 tests with real publication/submission, signed result, iframe scroll and ancestor enforcement. Application source is unchanged by this repair. Commit the test/documentation repair and rerun the full exact-HEAD gate before push. See the final entries in PROGRESS.md for evidence and explicit environment skips.
