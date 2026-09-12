# Integration cards and resource icons

The Integrations list defaults to cards with uploaded logos, optional descriptions,
authentication configuration, mapping counts, and authorization status. Desktop
users can switch to a table. Search includes descriptions; selection, export,
import, overflow actions, and the existing mapping workspace remain available.

Connection badges summarize saved OAuth token state across mappings. Completed
tokens count as connected; failed tokens need reconnection. These are not remote
service health checks. Integrations without OAuth configuration show “Not
monitored”; configured integrations without a connected or failed token show
“Not connected”.

## Shared icon contract

Use `ResourceIcon` for apps, forms, agents, and integrations:

- Card: 48px square.
- Table: 32px square.
- Inline: 24px square.

Prefer the response's `logo_url` and `logo_version`; pass `null` when no uploaded
logo exists to avoid unnecessary image requests. Missing or failed images use
the resource's selected icon or its type fallback. Uploaded artwork is contained,
not cropped. Fallbacks use the active primary branding color.

Apps, forms, agents, Home cards/lists, and collection resource selection share
this component. Form logos can be edited from the saved form editor header;
integration logos can be edited in the integration dialog. Logo changes save
immediately, independently of other draft fields. Solution-managed forms retain
the existing edit guard.

Integration descriptions round-trip through manifests and legacy JSON exports.
Uploaded image bytes remain runtime database state, matching existing app/agent
logo behavior; they are not included in those exports.

Generated sample artwork is in [sample-icons](sample-icons/README.md) and applied
to synthetic debug resources. It is optional resource content, not a replacement
for the branded fallback icons.

## Other refinements

Config retains a bounded, two-line Value preview. Values remain masked where
appropriate, and the editor retains the complete value. Entity Management omits
redundant collection loading rows while preserving error messages and retry.

## Verification

- TypeScript build check and scoped ESLint passed.
- Integration page/list/dialog: 15 component tests passed.
- Entity collection status: 2 component tests passed.
- Shared icons, form logo editor, form builder and resource consumers: scoped
  component tests passed; Home backend unit tests: 11 passed.
- Browser integration journey passed: edit description, upload SVG, reload,
  switch to table, and open the integration.
- Live debug inspection covered Integrations, Apps, Agents, and Forms at 390px
  and 1440px with no document horizontal overflow. Generated form and agent
  artwork and integration card layout were visually inspected.
- Live form-editor upload, thumbnail refresh, and Home search rendering passed.
- API logo URL and CLI parity/version checks: 41 passed. Manifest integration
  subset: 12 passed. Form-logo access and SVG sanitization subset: 3 passed.

Targeted commands included:

```sh
npm run tsc
npm test -- src/pages/Integrations.test.tsx src/pages/Integrations/IntegrationList.test.tsx src/components/integrations/CreateIntegrationDialog.test.tsx
npm test -- src/components/entity-management/EntityCollectionStatus.test.tsx
./test.sh client e2e integration-cards.admin.spec.ts --project platform-admin
./test.sh tests/unit/routers/test_entity_logo_urls.py tests/unit/test_contracts_parity.py tests/unit/test_contract_version.py
./test.sh tests/unit/test_manifest.py -k integration
./test.sh tests/unit/test_home.py
./test.sh tests/e2e/api/test_entity_logos.py::TestFormLogo tests/e2e/api/test_entity_logos.py::TestAgentLogo::test_svg_sanitized
```

The full backend, full browser, and pre-PR suites were not run for this slice.
The debug stack remains available; the branch is not merged.
