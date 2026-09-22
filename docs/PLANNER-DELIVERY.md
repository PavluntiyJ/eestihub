# Planner delivery and ownership

Status: proposed implementation handoff, 2026-09-21. M01/M03 are owner-assigned
planning work. These module IDs are distinct from existing T01–T20. This file
does not assign new application work or amend protected task briefs.

## Current parallel work

Codex owns PLANNER-PRODUCT.md, PLANNER-CONTRACTS.md, PLANNER-DESIGN.md,
PLANNER-DELIVERY.md and planner-preview.html. DeepSeek owns H2/H4 rework and
M02 probes/DATA-SOURCES.md under the owner's chat instruction. Neither edits
the other's new documents. TODO updates are small insertions after rereading
current content. Never stage or commit the entire shared working tree.

The CONTEXT owner must incorporate accepted additive endpoints and any new map
dependency before implementation. This pass leaves CONTEXT.md, AGENTS.md,
CLAUDE.md, tasks/ and the application's current API untouched.

### M02 report received during planning

DeepSeek's DATA-SOURCES.md is now available at [R]. Read as worker evidence,
not independently accepted here. It proposes In-AKS gazetteer, Tallinn GTFS,
Tallinn ArcGIS district geometry and OpenFreeMap Liberty. Keep these as adapter
candidates. Before geographic implementation, independently verify stable IDs,
CRS/coordinate order, the exact license covering each distribution/service,
attribution and redistribution requirements. In particular, a license attached
to older downloadable boundary files does not by itself establish the license
of the live ArcGIS layer. Gazetteer terms are explicitly unresolved in M02.
The report's observed HTTP responses do not provide an uptime guarantee.
These questions do not block M04–M06's provider-independent budget flow.

## Commit modules and gates

| Module / suggested commit | Deliverable / owned area | Required gate |
|---|---|---|
| M01 `docs(planner): define scope and proposed contracts` | Product, contracts, delivery docs | Review core formulas and supported audience |
| M02 `chore(data): verify address and transit sources` | Isolated probes, DATA-SOURCES.md | Actual request evidence, terms, CRS, identity, geometry and tiles |
| M03 `docs(design): specify Baltic planner screens` | Design doc + preview | Review responsive hierarchy and state coverage |
| M04 `feat(ui): introduce Baltic theme and navigation` | globals, shell, home, existing visual components, locale keys | H2 rework, M03; build + existing e2e/axe; visual review |
| M05 `feat(budget): calculate monthly and move-in budgets` | New schema/service/route/tests, router registration | Accepted M01 core contract in CONTEXT; Decimal boundary/unknown tests |
| M06 `feat(planner): add guided income and budget flow` | New planner feature/page/types, its locale keys, navigation | M04 + M05; browser salary/manual flow, retry, stale response, locale |
| M07 `feat(addresses): integrate verified address search` | Adapter, route/schema/tests, address combobox | Reviewed M02 + frozen geographic contract; timeout/empty/race tests |
| M08 `feat(transit): import and refresh GTFS snapshots` | Import scripts/service/models/tests and operations docs | Reviewed M02; feed checks, atomic switch, failed refresh recovery |
| M09 `feat(explore): add map and district layers` | Explore page/map leaf, geometry delivery, lazy dependency | M04 + M07 + approved tiles/polygons; no-map and mobile fallback |
| M10 `feat(apartments): assess entered apartment costs` | Assessment UI, nearby transport endpoint/UI | M05 + M07 + M08 + M09; unknown utilities, unresolved address |
| M11 `feat(housing): explain district affordability` | New enriched district endpoint/list, source metadata | M05 + M09; row-level provenance and partial data tests |
| M12 `feat(compare): compare apartment scenarios` | Comparison feature/page/locale keys | M10 + M11; 2–3 candidates, shared assumptions, no silent data loss |
| M13 `feat(scenarios): save and share relocation inputs` | Versioned serializer/storage/import/share controls | M12; privacy preview, size limits, corrupt/unsupported versions |
| M14 `test(planner): verify journeys and provider failures` | Cross-feature e2e and CI integration | M04–M13; full journey, outage, EN/ET/RU, light/dark and mobile |
| M15 `docs: document planner data and operations` | README/DEPLOY/runbooks/screenshots | Actual delivered behaviour, refresh commands, verified limits |

Keep tests and affected translations/docs with each feature commit. M14 is
cross-feature validation, not a deferred first test pass. Provider tests use
recorded permitted fixtures and deterministic fault cases; CI does not depend
on live provider uptime. Recheck live access manually at integration handoff.

## Next packet: M04–M06, sequential with separate commits

### M04 acceptance

- Existing four destinations retain their functions and URLs; no placeholder
  planner link until M06 lands. Home copy promises only implemented behaviour.
- Implement light/dark design tokens without raw colors scattered in components.
- EN/ET/RU navigation, skip link, focus styles, form labels and reduced motion
  preserved. Existing e2e/axe, production build and seeded Lighthouse pass.
- Review desktop/mobile screenshots and long Russian/Estonian labels.
- No backend/data-provider changes. README screenshots updated only once real.

### M05 acceptance

- Implement only core budget endpoint; no provider or database dependency.
- Check the four fixtures in PLANNER-PRODUCT.md plus exact allowance boundary,
  net=0, p=0/1, decimals/rounding, reversed summer/winter values, partial utilities,
  explicit zero versus missing move-in components, invalid/oversized inputs.
- Employment result equals the existing tooleping service; changing other regime
  rankings cannot affect it. Existing tax endpoint snapshots remain unchanged.
- Response shape/no-store and localized machine codes covered by API tests.
- Run backend suite and report additive contract for CONTEXT's owner.

### M06 acceptance

- Employment/manual net flow, explicit pension choice, E/S inputs and editable
  share; no success output before a valid current response.
- Editing/retrying preserves inputs; older responses cannot replace newer state.
- Existing calculator and locale switching remain functional. Form validation
  and calculation complete with keyboard alone; EN/ET/RU all have complete keys.
- Until M09, provide budget-only results and the existing housing tool as a
  clearly labelled general reference; do not ship a dead Explore CTA.
- Full build and browser tests against a real backend; failures preserve state.

## Documentation impact

These five planning files describe proposed behaviour; they do not make README's
current feature claims, deployment commands or test counts obsolete. No current
API/stack changes are authorized by writing a proposal. Before M04–M06 starts,
CONTEXT's owner must reconcile the supported audience, new route/schema, feature
structure and already-reported Docker documentation drift. M07–M11 depend on
M02 source evidence; do not freeze fictional integrations to keep a timetable.

At every packet boundary: inspect scoped diff, run the brief's checks, reread
affected documentation, record verdict, then assign the next packet. Workers
hand off at [R]; only the orchestrator accepts. No automatic M04–M15 marathon.
