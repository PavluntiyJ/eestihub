# Baltic planner UI — M03 design specification

Status: review-ready, 2026-09-21. Complements PLANNER-PRODUCT.md and the local
interactive `planner-preview.html`. The preview demonstrates budget and apartment
states using labelled fixtures; it is not the application or a live data source.

## Direction A

A calm Baltic relocation guide: editorial hierarchy and a sense of place on
the homepage, practical property comparison in the workflow, a map workspace
when geographic integrations are ready. Earlier Spotahome / Visit Estonia /
Komoot references describe these qualities, not a requirement to copy their UI.

The product answers one immediate question per screen. Lead with an outcome
and one action. Use large numbers where they help a decision, not generic metric
cards. Avoid a hero-sized heading on every tool page and nested cards in cards.

## Tokens to map onto existing shadcn variables in M04

| Role | Light | Dark | Use |
|---|---|---|---|
| Background | #F5F3EE | #101F2A | Warm canvas / navy canvas |
| Surface | #FFFFFF | #192E3B | Inputs, sheets, content |
| Foreground | #173042 | #EFF5F5 | Text |
| Muted foreground | #526675 | #B9CBD3 | Supporting text |
| Primary | #12685D | #8EDAC8 | Teal actions/selection |
| Primary foreground | #FFFFFF | #102A27 | Primary button text |
| Accent surface | #E0EDE8 | #203E3B | Selected context |
| CTA | #A84231 | #F0A28E | One main forward action |
| CTA foreground | #FFFFFF | #30180F | CTA text |
| Border | #CCD6D6 | #45616E | Structural edges |

These are proposed tokens, not certified contrast results. M04 verifies actual
text/surface pairs and focus indicators with axe and browser checks in both themes.
Never use pale coral with white body text. Map status also needs text/icon/pattern;
green versus red alone is insufficient. Dark maps require a compatible tile style
or a readable neutral map surrounded by the dark UI, not CSS inversion.

Keep Geist and the existing font loading setup. Desktop page title 40/44px,
mobile 30/34px; tool title 28/34px; body 16/24px; supporting text 14/20px.
Numbers use tabular figures; do not turn all UI text into monospace.
Spacing: 4, 8, 12, 16, 24, 32, 48, 64px. Control height >=44px, inputs 48px.
Card radius 20px, input radius 10px. Mostly flat surfaces; shadow reserved for
floating controls/sheets. Main max-width 1200px; content gutters 24px, mobile 16px.

## Screen specifications

### Home

Desktop: simple header; two-column hero with "Make your move to Tallinn add up",
one sentence explaining salary-to-housing planning, primary "Plan my budget",
secondary text link "Explore districts" once shipped. Right side: one licensed
Tallinn photograph with a small explanatory example, not an invented testimonial.
Below: three steps (income, housing, comparison), data transparency, existing tools.
Mobile: text and CTA first, image below; no full-height hero that hides the action.
Until an image is sourced with reuse permission, use typography and solid color.
No remote hotlinked decorative images or unverified statistics.

### Planner / income

Visible progress: Income → Budget → Explore. One form column <=560px and an
assumptions panel on desktop; stacked on mobile. Label gross as monthly EUR.
Employment is the visible default, not a hidden conversion from best regime.
Pension options 0/2/4/6% require a choice; offer manual net as an alternative.
Below submit: net estimate, current engine tax year, expandable calculation
assumptions. Validation focuses the first invalid field. No result for an empty
salary, no automatic persistence. Previous valid result is marked stale on edits.

### Planner / budget

Desktop: editable non-housing spending, savings and housing share on the left;
teal outcome panel on the right, showing total housing allowance and its two
limits. A small income strip allows going back without losing inputs.
Summer/winter inputs belong to apartment assessment, not this general allowance.
Primary CTA: "Explore within this budget". Secondary: "Check an apartment".
Explain that rent and utilities share the same allowance. A deficit takes the
place of celebratory copy; leave spending and savings editable.
Mobile: summary immediately after inputs, action in normal document flow.

### Explore

Desktop >=1024px: 380px scrollable list + remaining-width map, roughly viewport
height minus header and compact budget/filter bar. Filters: total rooms and
within-budget toggle; address search always accessible. Map and list selection
stay synchronized. Selecting a district opens its estimate and sources; selecting
an address opens assessment. Keep attribution clear of controls and sheets.
Do not automatically recenter on every background data update.
Mobile: list is default, explicit List / Map switch; selected detail opens a
bottom sheet with accessible close/focus return. No tiny side-by-side columns.

District row: name, selected room category, monthly rent + utilities range when
known, textual fit, source date. Separate "Published rent average" from
"Utilities assumption". Never render rows as live property listings.
If geometry/tiles fail, keep the list, budget and address form usable.

### Apartment assessment

Header: selected address or "Apartment A" when unresolved. Edit address/rent
without discarding the rest. Main content: seasonal totals and remainders, direct
cost inputs, move-in breakdown. Secondary content: nearby stops, route identifiers,
distance labelled "straight-line", feed date. Missing transit stays local to that
section. No commute minutes, safety ranking or neighbourhood personality claims.
Utilities mode switch: estimate / bills / unknown. Keep draft values when changing
tabs; unknown sends null amounts and excludes the draft values from calculations.
Returning to estimates restores the draft visibly before recalculation.
Primary CTA "Add to comparison"; explain the three-candidate limit before overwrite.

### Compare and save

Desktop: aligned columns for 2–3 candidates. Rows: entered rent, seasonal
utilities/totals, remaining budget, move-in cash, sources/missing information.
Mobile: vertically stacked candidates with the same row order; no forced horizontal
scrolling for essential numbers. Compare requires at least two; with one show
the candidate and an "Add another" action. Removing a candidate restores that state.
Save-on-device and Share are separate controls. Sharing opens a preview of included
salary/net/address fields with explicit toggles and Copy link; never silently copies.
Saved state is acknowledged in text, and storage failure offers export.

## State and interaction matrix

| Situation | Visible behaviour | Action/focus |
|---|---|---|
| Calculating | Existing result labelled Updating; submit disabled | Cancel obsolete requests; do not move focus |
| Invalid input | Error beside field, aria-invalid/describedby | Submit focuses first error; no API call |
| API unavailable | Entered values preserved; localized inline error | Retry; manual net only by user choice |
| Unknown utilities | Rent subtotal + unknown total/fit | Enter bills or choose an estimate |
| No district fits | All rows remain, explicit empty filtered state | Clear filter or edit budget |
| No address match | Distinct from provider failure | Edit query or continue budget-only |
| Map/WebGL unavailable | Full list and selected details | Retry map; no blocking dialog |
| Stale data | Source date and stale label | Explain source; do not claim freshness |
| Negative remainder | Signed deficit, text explanation | Edit assumptions; no green success styling |
| Locale/theme switch | Same inputs/selection persist | Keep keyboard focus on switch |

Loading skeletons reserve content size. One polite live region announces completed
calculations; never attach role=status to main. Address combobox supports arrow
keys, Enter, Escape and aria-activedescendant. List and forms provide all essential
actions without map gestures. Dialogs/sheets trap focus only while open and restore
it on close. Respect reduced motion and 200% zoom. Avoid toast-only feedback.

## Prototype and implementation review

`planner-preview.html` demonstrates the selected palette, budget inputs, seasonal
uncertainty, move-in breakdown and responsive hierarchy. Read-only employment
example uses the existing engine result; costs are illustrative user inputs.
It deliberately has no live map, providers, persistence or tax recalculation.
The full screen/state specification above is the handoff for remaining views.

M04: theme/shell/home and existing tools, EN/ET/RU and dark mode, no unfinished links.
M06: implement income/budget screens against reviewed M05 contract. M09–M12: map,
assessment and comparison after M02 and provider contracts are accepted.
Review at 390px and 1440px, 200% zoom, keyboard only, both themes and all locales.
Capture real implementation screenshots; do not substitute this prototype for e2e.
