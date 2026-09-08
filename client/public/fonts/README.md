# Bifrost fonts

Self-hosted WOFF2 fonts for the product and V1 host shell:

- Inter: interface text (400, 500, 600, 700)
- Prompt: display headings and wordmark (500, 600, 700)
- JetBrains Mono: code and identifiers (400, 500)

The latin and latin-ext subsets and `fonts.css` were obtained from the Google Fonts CSS API on 2026-09-05. Shared variable-font binaries are referenced by multiple weight definitions where the provider returned the same file. `font-display: swap` keeps text available while fonts load.

The sibling OFL files contain the licenses from `google/fonts` for each family. This directory is served locally; the running product makes no Google Fonts request.
