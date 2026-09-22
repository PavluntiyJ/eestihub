# Transit data license (GTFS import)

The GTFS snapshot imported by `python -m scripts.import_gtfs` is a derived
dataset. This file records what is licensed, what the project does with it,
and what is explicitly not covered.

## Source and licensor

Do not replace these with a guessed author; they are captured from the
recorded distribution and stored on every feed generation:

- Dataset: "Tallinna ühistranspordi peatused ja marsruudid" (Tallinn public
  transport stops and routes), via `https://transport.tallinn.ee/data/gtfs.zip`.
- Registry evidence:
  `https://avaandmed.eesti.ee/api/datasets/5ccad39d-98a0-4ac4-ba0a-233ad5a83604`
  lists license `CC_BY_SA_3.0`, access URL `http://transport.tallinn.ee/data/gtfs.zip`
  and applicable legislation `ODD_LEGAL_ACT` (recorded 2026-09-21).
- Primary license text:
  https://creativecommons.org/licenses/by-sa/3.0/legalcode.en

## What the CC BY-SA 3.0 covers

The imported and normalized transport rows stored in this database
(stops, routes, scheduled stop/route/service relationships, calendars and
exceptions) are distributed derived data under **CC BY-SA 3.0**. The
retained evidence names Tallinn and the distribution — no authorship
beyond that is claimed. The stored credit reads: "Tallinn public
transport stops and routes (Tallinna ühistranspordi peatused ja
marsruudid) via transport.tallinn.ee", plus the registry URL above and
the license URL. `GET /api/v1/transit/nearby` carries this stored credit,
license URL and transformation record; the frontend displays source/license
links, credit and check/source dates next to the stop list.

Transformations applied (recorded per generation in `transit_feeds`):
source rows are filtered to the needed entities, stop/route pairs are
deduplicated with their service IDs, coordinates are parsed to numbers and
route types keep their raw code plus a derived mode label
(tram/bus/trolleybus/other). Trips, stop times, shapes and agency rows are
transient join inputs and are not stored.

## What it does not cover

- Independently written project code (backend, frontend, scripts, tests)
  stays under the repository's MIT license.
- Salary, budget and scenario data never enter the transit tables and are
  not combined into the licensed transit dataset.
- This file does not claim that all service software or all database
  contents carry CC BY-SA 3.0 — only the transit rows described above.
- The owner-authorized planner release uses the retained source-license
  evidence and attribution above. M08 itself did not publish or deploy.
