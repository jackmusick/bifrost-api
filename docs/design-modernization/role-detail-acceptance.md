# Role Detail acceptance

Routes: `/roles/:roleId` and `/roles/:roleId/:tab`. Parent owns visual acceptance. This page consolidates existing evidence; it does not require repeating every historical fixture.

| Requirement | Evidence | Status |
| --- | --- | --- |
| Responsive header, long identity, all six tabs, edit/delete entry | Browser35006, light/dark320/768/1440; parent inspected header and current Users/Forms/Agents/Apps/Workflows/Knowledge captures | Verified |
| Initial and cached role reads, retry, selected tab retention | Browser23642, six cases; source RoleDetail retains cached role and currentTab | Verified |
| Edit pending guard, failure/retry, draft and unknown permission preservation, refresh and cancel focus | Browser13506, six cases; RoleDialog tests72106 | Verified |
| Delete confirmation, pending dismissal guard, failure/retry, navigation | Browser39853, six cases; parent inspected dark320 error | Verified |
| Shared consumer selection, assignment drawer, pending guard and retry | Browser81582 and actual Users flow; ConsumerTab tests28770 include removal error beside action | Verified |
| Users assignment/removal with visible mobile recovery | Parent browser76349 four cases; final mobile footer65435 inspected | Verified |
| Forms, Agents, Apps, Workflows endpoint-specific assignment/removal | Parent `role-consumer-endpoints.cjs`84368: all16 light/dark320/1440 cases passed exact body keys, assignment/removal failures and retries; no page errors | Verified |
| Assigned/candidate initial and cached errors, failed search | Browser33667 six cases; current source wires read-state contracts to all five entity consumers | Verified |
| Knowledge mobile records, namespace/scope validation, read retry, assignment/removal and pending state | Browsers24153,64148,24501 six cases each; parent inspected mobile and desktop current captures | Verified |
| Custom brand and reduced motion | Populated custom purple Users capture inspected; current generic endpoint fixture uses Northwind custom branding and reduced motion; semantic error/status colors preserved; final16cases passed | Verified |
| Full route signoff | Parent inspected final Forms light320 and Workflows dark1440 removal recovery; all listed UI requirements reconciled | Verified |

Synthetic mutations prove client contracts and recovery; they do not claim backend authorization or production writes. Shared authorization and final release gates remain in the global matrix.
