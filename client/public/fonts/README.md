# Bifrost fonts

Self-hosted WOFF2 fonts for the product and V1 host shell:

- Inter: interface text (variable 100-900)
- Prompt: display headings and wordmark (500, 600, 700)
- JetBrains Mono: code and identifiers (variable 400-800)

The latin and latin-ext subsets and `fonts.css` were obtained from the Google Fonts CSS API on 2026-09-05. Inter and JetBrains Mono are variable-font binaries, so their `@font-face` rules declare the supported weight ranges instead of repeating the same binary under separate static weights. Prompt is served as static weight files. `font-display: swap` keeps text available while fonts load.

The sibling OFL files contain the licenses from `google/fonts` for each family. This directory is served locally; the running product makes no Google Fonts request.
