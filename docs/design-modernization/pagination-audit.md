# Pagination Audit

Inspected during the History preview and pagination shell pass.

## Fixed in this pass

- History workflow executions (`client/src/pages/ExecutionHistory.tsx`, `client/src/hooks/useExecutions.ts`): changing only `continuationToken` now keeps the previous page data mounted while the next page fetch is pending. The table is marked `aria-busy`, the shared pagination footer shows pending state, and Previous/Next are disabled until the fetch settles. Retention requires the same scope and filters, so an organization or status/date/workflow filter change does not show stale rows.
- History logs (`client/src/pages/ExecutionHistory/components/LogsView.tsx`, `client/src/hooks/useLogs.ts`): changing only `continuation_token` keeps the current log page mounted while pending. Filter changes remount `LogsViewInner` and also fail the same-filter placeholder guard.
- Audit log (`client/src/pages/audit/AuditLogPage.tsx`, `client/src/hooks/useAuditLog.ts`): changing only `continuation_token` keeps audit rows mounted, marks the table busy, shows the footer pending spinner, and disables pagination controls. Other audit filters must match before old rows can be reused.
- Table documents (`client/src/pages/TableDetail.tsx`, `client/src/services/tables.ts`): changing only document `offset` keeps the current document list mounted while pending. Retention requires the same `table_id` path and the same non-offset query body, so table changes and filter/page-size changes do not reuse rows.

The shared helper is `client/src/lib/paginated-query.ts`. It compares query-key request params or path/body values while excluding only the page cursor/offset field for the specific hook.

## Already safe or different pagination model

- Users (`client/src/hooks/useUsers.ts`, `client/src/pages/Users.tsx`): `useUsersPage` already uses `placeholderData: keepPreviousData`; the page shell marks the list area busy and `ListPagination` disables controls while fetching. This is existing broad React Query retention, not the scoped same-filter helper added in this pass. Its query key includes the full page params including scope, search, sort, limit, and offset, but `keepPreviousData` still means the immediately previous key can be shown while a new key is pending.
- Roles (`client/src/hooks/useRoles.ts`, `client/src/pages/Roles.tsx`, `client/src/components/roles/ConsumerTab.tsx`): role list and role-user pages already use `placeholderData: keepPreviousData`; consumers pass busy state into the table/list and pagination controls. This is also existing broad retention. Even though role-user query keys include `roleId`, `keepPreviousData` can carry the immediately previous role-user page during a pending role change; that behavior is documented here but not changed in this bounded task.
- Platform jobs (`client/src/pages/diagnostics/components/PlatformJobsPanel.tsx`): already uses explicit placeholder retention only when search and status filters match while offset changes.
- Agent runs in History (`client/src/components/agents/AgentRunsPanel.tsx`): uses client-side pagination over loaded/infinite run data, not a new server page query that empties the table shell on Next.
- Home browse (`client/src/pages/Home/components/HomeBrowse.tsx`): client-side paging over loaded catalog data; not part of the server-page shell bug.
- Execution details and execution result pagination (`client/src/pages/ExecutionDetails.tsx`): intentionally outside this task scope and not the History list shell.
- Reports/ROI usage tables: static tabular summaries from report data, not interactive server pagination shells.

## Remaining notes

No global React Query `keepPreviousData` setting was added. Retention is opt-in at the hooks that back the affected pagination shells, and each guard includes the relevant permission or data-boundary fields in the comparison.
