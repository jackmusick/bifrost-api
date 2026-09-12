# Component evidence reconciliation

The64 routes and14 families are UI Verified. The per-source inventory contains151 page modules,53 primitives and374 feature components (578 total). All578 asset records are now UI Verified. Existing isolated evidence was reconciled with final consumer acceptance, and23 legacy evidence fields were normalized into rendered_proof. Each asset retains route/global ownership metadata. Reachability identifies consumers; acceptance also requires the linked reviewed source, rendered evidence and behavior checks.

Scratch ownership map: /tmp/bifrost-design-review/component-consumers.json. It resolves52 route modules (including lazy bindings,0 misses) plus main.tsx/global App. The main entry point matters for Toaster and OrgScopeQueryInvalidator. Public runtime registries also make hover-card and slider reachable.

The25 files below have no detected path from those roots. Their compatibility intent and isolated evidence are reconciled in retained-component-review.md; all are retained. This list does not mean25 reachable pages remain undesigned.

- `client/src/pages/ExecuteForms.tsx`
- `client/src/pages/diagnostics/components/QueueSection.tsx`
- `client/src/pages/settings/GenerationModelSettings.tsx`
- `client/src/pages/settings/ModelCapabilityEditor.tsx`
- `client/src/components/ui/verdict-toggle.tsx`
- `client/src/components/agents/Chip.tsx`
- `client/src/components/agents/FleetStats.tsx`
- `client/src/components/agents/KVList.tsx`
- `client/src/components/agents/MetaLine.tsx`
- `client/src/components/agents/NeedsReviewCard.tsx`
- `client/src/components/app-builder/AppUpdateIndicator.tsx`
- `client/src/components/app-builder/NewVersionBanner.tsx`
- `client/src/components/editor/ChangesList.tsx`
- `client/src/components/editor/ConflictResolutionBanner.tsx`
- `client/src/components/editor/FileTree.tsx`
- `client/src/components/editor/FileTreeContextMenu.tsx`
- `client/src/components/editor/FileTreeNode.tsx`
- `client/src/components/forms/FieldsPanel.tsx`
- `client/src/components/forms/FormInfoPanel.tsx`
- `client/src/components/oauth/OAuthConnectionCard.tsx`
- `client/src/components/oauth/RefreshJobStatus.tsx`
- `client/src/components/schedules/CronTester.tsx`
- `client/src/components/tables/DocumentQueryPanel.tsx`
- `client/src/components/users/UserDetailsDialog.tsx`
- `client/src/components/users/UserRolesDialog.tsx`

The full client suite passed453 files /2690 tests before the final retained repairs. The final13 focused tests pass, along with21 API/compiler boundary tests. Exact-candidate pre-pr reruns the broad client/backend/live-smoke checks after commit.
