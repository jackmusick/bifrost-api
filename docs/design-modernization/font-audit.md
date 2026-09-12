# Font Audit

Audit date: 2026-09-08

Scope: platform-hosted client fonts and font-family overrides in `client/src`, excluding `ExecutionHistory` and `workflow` files.

## Canonical Stacks

- UI text: `Inter`, through `--bf-font-sans` / `--font-sans`.
- Display headings and product identity: `Prompt`, through `--bf-font-display` / `--font-display`.
- Code, identifiers and measurements: `JetBrains Mono`, through `--bf-font-mono` / `--font-mono`.

## Asset Metadata

`fc-scan` was used against `client/public/fonts/*.woff2`.

- `inter-latin-400.woff2` and `inter-latin-ext-400.woff2` identify as Inter variable fonts. They expose Thin through Black instances and a variable weight range, so `fonts.css` now declares `font-weight: 100 900` for each subset instead of repeating the same file for 400, 500, 600 and 700.
- `jetbrains-mono-latin-400.woff2` and `jetbrains-mono-latin-ext-400.woff2` identify as JetBrains Mono variable fonts. They expose Regular, Medium, Bold and ExtraBold instances; `fonts.css` now declares the CSS weight range those instances cover, `font-weight: 400 800`, instead of repeating the same file for 400 and 500.
- Prompt files are static per weight. The internal names for 500 and 600 report `Prompt Medium` and `Prompt SemiBold`, but the CSS `font-family: 'Prompt'` wrapper correctly presents them as one display family to the product.

## Overrides Checked

- Monaco wrapper options already used JetBrains Mono in the primary app editors. The shared Monaco hook now uses the same fallback stack as those wrappers.
- Markdown inline code now resolves through `--font-mono`, preserving JetBrains Mono for rendered code snippets.
- App SDK host header chrome and Monaco conflict widgets now resolve through `--bf-font-sans`, preserving Inter in host-owned UI.
- No literal `Monaco` font-family override was found in `client/src`.
- `SafeHTMLRenderer` and E2E fixture font resets remain unchanged because they are sandbox/default content fallbacks rather than host UI chrome.

## Verification

- `fc-scan --format ... client/public/fonts/*.woff2`
- `npx eslint src/hooks/useBifrostMonacoTheme.ts src/lib/app-sdk/bifrost-header.tsx src/lib/monaco/conflictWidgets.ts`
- `git diff --check -- client/public/fonts/fonts.css client/public/fonts/README.md client/src/hooks/useBifrostMonacoTheme.ts client/src/index.css client/src/lib/app-sdk/bifrost-header.tsx client/src/lib/monaco/conflictWidgets.ts docs/design-modernization/font-audit.md`

Parent verification: Chromium's platform-font inspection on rendered History
confirmed Prompt SemiBold for the heading, Inter for the search input and table
text, and JetBrains Mono for workflow identifiers. This checks actual glyph fonts,
not only CSS family names. TypeScript and scoped ESLint for the three changed
TypeScript font overrides passed. This source audit does not claim every route
was visually inspected or that app-authored fonts are overridden.
