# Legacy components fixture commands

This fixture seeds a real inline v1 app in the debug instance and writes the
app source through the supported CLI file surface. The live app is named
`Design Review Legacy Components`.

## Source files

- `fixtures/legacy-components/pages/index.tsx` — v1 app source that imports
  `Button` with `asChild`, `Card`, `Input`, `Select`, `Dialog`,
  `CommandDialog`, `Tabs`, and `CalendarPicker` from `bifrost`.

## Expected routes

- Preview: `/apps/design-review-legacy-components/preview`
- Live: `/apps/design-review-legacy-components`

## Recreate in the seeded debug instance

```bash
cd /tmp/bifrost-cli-design-system-modernization
./.venv/bin/bifrost auth default
./.venv/bin/bifrost apps create \
  --name "Design Review Legacy Components" \
  --slug design-review-legacy-components \
  --app-model inline_v1 \
  --access-level authenticated
./.venv/bin/bifrost files write apps/design-review-legacy-components/pages/index.tsx \
  --from-file /home/jack/GitHub/bifrost/.claude/worktrees/design-system-modernization/docs/design-modernization/fixtures/legacy-components/pages/index.tsx \
  --create-only
./.venv/bin/bifrost apps publish design-review-legacy-components
```

If the target instance already has a placeholder page, read it first and
rewrite with `--expected-version <version>` instead of `--create-only`.
That is the path this seeded debug instance required.

## Notes

- The app source uses only the public `bifrost` import contract.
- The app is intentionally synthetic and self-contained.
- No external integrations or credentials are required.
