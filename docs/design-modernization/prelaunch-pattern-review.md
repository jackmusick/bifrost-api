# Platform pattern review — 2026-09-09

This review concerns Bifrost's platform shell and reusable controls, not the
content or layout of a hosted customer app. It is a bounded review of resource
cards and History pickers, with design recommendations from the current Home,
Integrations, and History surfaces. It is not a complete release sign-off.

## Verified findings

- **App-card alignment drift (corrected):** `ApplicationListSurface` centered its
  card icon against the title while the Forms, Agents, Home, and Integration
  card layouts aligned their identity rows at the top. The app-card row now
  uses top alignment and the same 12px gap. Table rows retain centered icons.
- **History trigger-width report (not reproduced):** the workflow and organization
  pickers both use shared `PopoverContent variant="picker"`. In the current
  debug build, their 176px desktop triggers open 320px panels. The organization
  name wraps instead of being truncated. A browser regression test now checks
  both picker widths, search, dismissal, and mobile viewport containment. The
  user's reported failure remains unconfirmed; do not describe it as fixed.
- **Unnamed picker triggers (corrected):** the searchable workflow picker had
  no explicit accessible name, and organization scope could omit one when its
  caller supplied no label. Shared fallbacks now name both controls; explicit
  organization labels and labelled-by relationships remain supported.
- **Review access interruption (restored):** the NetBird sidecar had exited while
  the app containers remained healthy. Restarting it created a new public URL;
  the debug launcher applied that URL to the API and execution services.

## Recommendations before launch

1. **Consolidate card identity layout.** `ResourceIcon` standardizes the artwork
   but not its surrounding title/action layout. A small shared card-header
   component would prevent alignment and spacing drifting again. Keep each
   resource's content and meaningful actions distinct.
2. **Make integration status the summary.** Cards currently repeat Authentication,
   Organization mappings, and Connection status on every item. A prominent
   status summary and mapping count would scan faster; configuration details
   can be quieter. Keep “Not monitored” honest and never imply a live health
   check from stored OAuth state.
3. **Finish the resource icon vocabulary.** Home category headings use FileInput
   for forms while the shared form-card fallback is FileCode. Choose one form
   symbol in a shared resource-kind definition. Resource artwork should stay
   consistent between Home, management lists, and selection dialogs.
4. **Keep Home focused on launching.** The category overview is already a useful
   improvement over one wall of cards. Prefer recognizable artwork, favorites,
   and a clear title; don't add management metadata to make those cards resemble
   the administrator lists.
5. **Preserve History density and readable identity.** Date grouping is now more
   visible. Consider normal UI type for human-facing workflow titles, reserving
   monospace for identifiers and log/code content. Retain the compact filters,
   stable pagination, and bounded table scrolling.

These are proposals for review, not additional redesigns silently applied.
The next visual acceptance pass should include long names, missing artwork,
custom branding, light mode, mobile keyboard-open pickers, and active execution
states. These conditions are not all covered by this bounded pass.

## Scoped checks

- `npm test -- src/pages/Applications.test.tsx`: 11 passed.
- `npm test -- src/components/forms/WorkflowSelector.test.tsx src/components/forms/OrganizationSelect.test.tsx`: 19 passed.
- TypeScript build check and scoped ESLint passed.
- Apps visually reviewed at 390px and 1440px; neither had document overflow.
- `./test.sh client e2e history-pickers.admin.spec.ts --project platform-admin`
  checks real compiled picker geometry and behavior. The initial run exposed
  missing accessible names, which were corrected in the shared controls.
  Final run: 2 passed, including authentication setup and the desktop/mobile
  picker journey. A subsequent test-selector mismatch was corrected to use
  the mobile button’s existing “Show filters” accessible name.

Full suites and the pre-PR gate remain outside this scoped review.
