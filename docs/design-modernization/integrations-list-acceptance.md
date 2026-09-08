# Integrations list acceptance

Status: UI Verified. Scope is `/integrations`, including its create/edit/import dialogs. Integration detail is reviewed separately.

## Current interaction pattern

Record names are native links. Desktop rows additionally support row navigation. Both desktop and mobile use one shared RecordActionsMenu for secondary Edit/Delete actions; there is no separate Open arrow. Mobile uses wrapping cards, and selection/export remain explicit list actions.

## Evidence

| Area | Current proof |
| --- | --- |
| List/actions | Parent browser24940: four320/1440 light/dark custom-purple reduced-motion cases. Link targets, keyboard menu open/Escape focus,44px triggers, selection/export, pending/failed delete retry and cached-refresh recovery. Parent inspected mobile dark cards. Four component tests16476 and lint17637 pass. |
| Create | Browser55097: four320/1440x600 cases with five schema fields. Footer stays visible, pending Save guards Escape/Cancel, failed POST retains all fields and retry payload, success closes, reopen is clean, Cancel closes. Parent inspected dark320. |
| Edit | Browser11434: four320/1440x600 cases, whitespace-name validation prevents PUT, restored name/default id retained through pending failure and retry. Shared form footer and error stay visible. Final browser94505 repeats all four cases after waiting for the earlier validation toast to expire; parent inspected the unobstructed light320 footer/error capture. |
| Shared form | Eight CreateIntegrationDialog tests30343 pass, including edit lookup recovery, provider retry, confirmation sequencing, exact payload and pending dismissal. Scoped lint41499 passes. Prior loaded-edit and provider/schema confirmation artifacts remain in PROGRESS.md. |
| Import | Final browser3776: four320/1440x600 cases. Invalid JSON feedback, valid selected file, pending input/close guard, failed import retained for retry, visible fixed footer/error, success Done, reopen/reset and cancel. Parent inspected dark320 final error capture. All imports intercepted. |
| Shared import | Four ImportDialog tests69645 pass, including held import dismissal protection and JSON/ZIP consumers. Input controls are disabled while pending; close and file replacement handlers also guard pending state. Duplicate failure toast removed in favor of inline feedback. |
| Quality | Full TypeScript9798 passed; final scoped lint82691 passed after footer/feedback changes. |

The initial create script captured only an open form. The original list harness expected removed direct Open/Edit/Delete buttons. Those artifacts are superseded by the checks above. Modal work has been reconciled rather than left as a blanket pending item.

## Limits

Browser requests use synthetic integration records and intercepted mutations; this proves UI behavior and request payloads, not provider connectivity or persisted organization mappings. The separate `/integrations/:id` route and application-wide build/test/delivery gates remain open.
