# New form designer acceptance

Status: UI Verified. Scope: `/forms/new`, using the shared designer, metadata and field configuration components. Existing-form editing and runtime/embed execution have separate acceptance.

New forms start with Form Information. Metadata selection, field creation and Save remain recognizable. Save owns its pending interval across form and role writes; editing/navigation pause until it finishes. Failed role assignment keeps the created ID and draft, explicitly explains the partial save, and retries by updating the existing form. Success is announced only after all save steps complete. Platform-admin route access is retained in App.tsx.

| Area | Evidence |
| --- | --- |
| New-form flow | Browser6902 and final69508: four custom-purple light/dark320/1440x600 name/workflow/role selection, local text field creation, successful POST followed by held role500, pending control protection, focused partial error, retry PATCH to the created ID, role retry and destination. Exactly one create and one retry update. Parent inspected final dark320. |
| Shared field dialog | Browser42190: four matching cases for fixed footer, required state, file options, mobile context, local update/reopen/cancel. Twelve FieldConfigDialog tests29889 cover normalized names, invalid names/visibility, save readiness, text payload and radio/multiselect/file controls. Parent inspected mobile and desktop. |
| Shared designer | Existing edit-save65660/final16406 prove pending inert canvas, retained field order, inline failure/retry and destination. Context/launch dialogs83875 and read recovery60723 have current branded mobile/desktop evidence in PROGRESS. |
| New identity regression | Five FormBuilder tests58207 pass, including create→role failure→update retry without another create, plus launch and read recovery. |

Browser mutations are intercepted; no actual forms or access assignments were created. Shared schema/runtime compatibility and application-wide release gates remain tracked separately. This acceptance does not claim real workflow execution, external provider behavior or existing-form access reassignment correctness.

Final scoped lint/full TypeScript26432 and touched-source diff check pass. Toast options default to the prior behavior for other create/update consumers; the designer owns its combined-save notification.

Metadata footer correction: final20639 passes all4 custom-purple320/1440x600 light/dark explicit Save/Cancel bounds and retained metadata cases. Parent inspected dark320. Seven metadata tests86938 and lint/TypeScript37194 pass.
