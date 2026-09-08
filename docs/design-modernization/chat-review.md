# Chat and artifacts review — 2026-09-08

Both routes are UI Verified after the final reconciliation below. Prior chat setup/navigation/header/composer/message/tool and artifact read/record/recovery scripts remain evidence; current browser checks use synthetic API/WebSocket fixtures and the active0-38 NetBird preview.

Parent artifact read42878 passes four light/dark320x480/1440x900 initial/cached failure, recovery and filter reset cases. Dark320 cached failure image reviewed. The list uses mobile records; rename/delete dialogs need bounded bodies, fixed actions and explicit error/opener/removal focus. Bounded agent extraction assigned in authorized worktree only.

Parent header26424 passes four current read recovery/header/usage popover cases after correcting fixture auth/me role data. Parent narrow screenshot exposed long conversation title consuming excessive height, so mobile title now clamps to two lines and agent subtitle to one, preserving full semantic text and desktop wrapping. Subsequent9369 hit transient module MIME failure during source edits and is not accepted as final proof. Final stable browser rerun due.

Parent ChatInput now shows persistent inline send failure and keeps the restored draft for retry; ChatWindow no longer duplicates the failure in a transient toast. Fifteen focused ChatInput tests55193 pass including retained draft, error feedback and exact retry. Current route browser send failure proof and combined TypeScript remain due.

## Current composer, header and artifact evidence

Header73961 passes four light/dark320x480/1440x900 history recovery, long title, usage popover and Escape/focus cases. Parent inspected closed light320 header after mobile title clamp. Composer35482 passed send recovery, but parent screenshot inspection exposed long draft plus attachment pushing Send below the viewport. Parent bounded composer height relative to its available column, made draft/attachment content scroll, kept actions fixed and model label truncated with full selector options. Final79873 passes four cases with explicit Send bottom bounds, attachment removal, held send failure, persistent inline feedback, restored draft and exact retry. Parent inspected light320 long draft and failure states.

Artifact extraction uses ArtifactDialogs and explicit Manage refs from ArtifactRecord. Seven agent tests passed. Parent39917 passed four rename/delete pending/error/retry/focus cases;62817 added long filename Cancel/focus/bounds. Parent then moved delete description into scrolling body to remove the empty error-region gap and handle long filenames. Final13687 passes all four cases; parent inspected light320 long-name confirmation and dark320 failure with fixed actions. Earlier rename success toast could overlap a rapidly opened next dialog; the supplemental screenshot waits for its normal dismissal. Toast/modal stacking remains a shared-family review item.

## Brand-new conversation transition

Parent31428 demonstrated loss of the failed draft when new conversation navigation remounted the route. Parent added an explicit preserveChatDraft navigation state only to newly created conversation navigation, corresponding route-reveal key handling, and stable composer child keys across ChatWindow branches. Ordinary conversation/artifact navigation retains its previous route keys. Transitional86379 was invalidated by source changes while running; final40871 passes four new-conversation URL transitions, held send failures, restored drafts/inline feedback and exact retries. Five focused test files6876 pass39 tests, including route-state boundaries and existing optimistic text/attachment staging. Final lint/full TypeScript34086 pending.

## Route acceptance

Final scoped lint/full TypeScript34086 pass after the new-conversation lifetime correction. Current artifact records69652 pass four theme/width cases for long filename/conversation wrapping, menu, filters and search; parent inspected dark320 and light1440 records, plus dark1440 closed Chat header. Parent accepts both Chat routes using the prior setup/navigation/message/tools evidence and current route-level checks above. Current total62 Verified/2 In progress; only Layout and ContentLayout route rows remain open. Shared-component/V1/custom branding/full-suite/build/release/deployed-candidate gates are still separate and incomplete.
