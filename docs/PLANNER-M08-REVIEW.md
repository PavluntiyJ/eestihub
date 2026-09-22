# M08 review corrections — 2a4f754

## Final implementation follow-up — 2026-09-22

Muse's `ad87972` corrected the subprocess download deadline and zlib failure
normalization. Independent code review found the first `session.flush()` still
outside its IntegrityError retry boundary. Codex's `8db2efe` wraps the complete
transaction attempt (including staging flushes), rolls back and retries once;
a real same-SHA PostgreSQL barrier test exercises the contested first insert.
Local full suite after nearby-transit integration: 240 passed, 5 PG skipped.
PostgreSQL CI on `3906256` passed all 245 backend tests, including all five PG
integration cases. **M08 is accepted.** The action lists below are historical.

## Re-review of 2d35cfa — current action list (2026-09-22)

**Three groups remain open.** The original findings below are historical;
do not reimplement the corrected calendar, freshness, CI or attribution work.
Independent full backend run: **230 passed, 4 PostgreSQL skipped**;
frontend build and lint passed. PostgreSQL is now wired into the backend CI
job with an explicit test URL and fail-on-unavailable behavior, but this
review did not run GitHub CI or claim a PostgreSQL pass.

### R1. P1 — response.close() does not enforce the total deadline

`backend/app/services/transit_import.py:227-246`

The real HTTP regression still fails: loopback HTTPServer sends a 40-byte
body one byte every 20 ms, with Content-Length=40. Patched urlopen delegates
to the real urllib opener against that server. With deadline_s=0.1 and
timeout_s=0.2, download_source raises only after **0.812 seconds**, when the
body has finished. response.close() waits on the buffered reader while the
pump owns it; it does not interrupt this blocking read. urlopen also runs
synchronously before the supervised thread, so delayed headers are outside
the cancellable section. Temporary file cleanup is fixed in this reproduction.

Use cancellation that actually interrupts and reaps the transfer within a
small bounded teardown allowance, covering connection/headers/body. A stdlib
subprocess with parent-owned temporary-file cleanup is one possible design;
if using sockets, prove shutdown interrupts real reads before closing the
buffered response. Do not leave a daemon doing I/O after returning an error.
Close resources on success, HTTP error, size failure and cancellation.

Replace/supplement the current fake DripResponse test: its close() simply
sets a threading.Event, unlike urllib's actual response. Use a real loopback
HTTP server for slow body and delayed headers, bounded test timing, assert
transfer termination and no temporary files. No upstream network needed.

### R2. P2 — active SHA checks remain unsynchronized; retry misses flush

`backend/app/services/transit_import.py:1014-1025,1061,1114-1117`

1. checked_at is assigned unconditionally, outside the state-row lock. A
   sequential regression already proves the bug: import/check A at 12:00,
   then complete an older A check stamped 11:00 -> stored checked_at becomes
   11:00. Preserve the maximum successful check time using database-safe
   synchronization, and resolve actual active identity under the same
   synchronization as activation so a concurrent flip cannot make an
   inactive feed return already_current.
2. The initial session.flush() inserting TransitFeed is outside both
   IntegrityError handlers. A same-SHA unique race fails there, before the
   new retry code runs. Independent two-session reproduction: pause worker A
   immediately before INSERT transit_feeds after its initial SHA lookup;
   let worker B activate the same SHA; resume A. B returns activated,
   A raises IntegrityError. This was reproduced on a disposable SQLite DB
   to exercise the code path, not offered as PostgreSQL locking evidence.

Enclose all relevant staging flushes in the bounded race-recovery boundary;
roll back and re-resolve expected unique races without retrying arbitrary
invalid data forever. Add actual same-SHA overlap tests (the four current
PostgreSQL checks do not cover this case), monotonic checked_at tests and an
active-recheck-versus-new-generation overlap. Keep retained-SHA refusal and
unconditional stale-activation checks, which are fixed.

The documented superseded/no-op exit 0 convention is accepted for this
internal CLI; do not expand scope to rework it. Actual import/database errors
must still return nonzero and cannot be relabeled as superseded.

### R3. P2 — corrupt DEFLATE still escapes the invalid-feed handler

`backend/app/services/transit_import.py:414-417`

The read catches BadZipFile/OSError/EOFError but not zlib.error. Independent
reproduction: create a valid ZIP_DEFLATED fixture and set the first compressed
byte of stops.txt to a reserved DEFLATE block type (low bits 0b111), retaining
the central directory. parse_feed raises raw zlib.error (not FeedError),
so the CLI's FeedError handler is bypassed and a traceback is printed.

Normalize decompression errors as promised, preserve cleanup, and add both
parser and real CLI regression tests asserting exit 1 with no traceback.
The previous CRC test is not a substitute: CRC corruption and malformed
compressed streams fail through different exception paths.

### Re-review delivery

Fix R1-R3 only in another logical fix commit, add regressions, run full
backend tests and build/lint, and report PostgreSQL execution honestly.
Update only assigned docs and your TODO insertions. Preserve unrelated
working-tree changes; no M09, push, production import or deployment yet.

---

Codex, 2026-09-22. M08 needs corrections before M09. This packet supplements
PLANNER-M08-HANDOFF.md; it does not authorize a production import, push or
deployment. Preserve the unrelated TODO, dictionaries and planning documents.
Implement the fixes in a separate conventional commit and stop for review.

## Independent verification

- Full backend suite: **191 passed, 3 skipped**, not 150 passed. The three
  skipped tests require PostgreSQL. No local PostgreSQL executable/server was
  available; no PostgreSQL concurrency safety claim is made.
- Frontend production build and lint passed. No frontend changes in M08;
  this review did not repeat the worker-reported 62 browser tests.
- Independent probes used synthetic archives, an in-memory SQLite database
  and a loopback HTTP server. No production database or upstream was changed.
- Existing tests miss the reproductions below. Fix the behavior and add
  regression coverage; do not weaken assertions to match the current code.

## 1. P1 — stale activation and incorrect SHA idempotency

`backend/app/services/transit_import.py:715-718,742-755`

The age comparison only runs when active_feed_id differs from based_on, but
based_on is captured after download and parsing. An older download that
finishes parsing after a newer activation sees the newer pointer as based_on
and overwrites it. Reproduction: activate A fetched at 12:00, then call the
normal import path for B fetched at 11:50. Both return activated and B wins.
The existing stale-generation test forces based_on=None inside a monkeypatch,
which hides this case. Protect activation against stale work regardless of
whether it was delayed before or during the staging transaction.

The SHA shortcut searches all retained feeds, not the active one. After A
then B, importing A again returns already_current/feed_id=A while B remains
active. Restrict already_current to an actually active generation checked
under the activation synchronization. For a retained non-active SHA, either
reactivate it under an explicit safe policy or return an honest non-current
outcome; never claim it is current. A stale concurrent recheck must not move
checked_at backward or report successful freshness for an inactive feed.

Regressions: older parsing finishes after newer activation; existing-active
and initially-empty concurrent writers; active SHA recheck; retained SHA
A -> B -> A; concurrent same-SHA checks with different check times. Retain
old-generation reads and atomic rollback assertions with a good active feed.

## 2. P1 — download deadline is not a total bound; failure leaks files

`backend/app/services/transit_import.py:175-218`

response.read(65536) can stay blocked while a peer sends bytes more frequently
than the socket timeout. Checking the clock before that call does not enforce
a total deadline. Loopback reproduction: one byte every 20 ms, socket timeout
200 ms, total deadline 100 ms; download returns an error only after ~610 ms.
At the production constants a slow response can exceed 60 seconds greatly.
The current fake-clock test fails before any read, so it does not test this.

Use a deadline-aware streaming transport that bounds blocking operations,
including receiving headers/body, and actually stops the I/O on expiry.
Do not merely time out a waiting caller while leaving the transfer running.
Keep stdlib/no retries and fixed-source restrictions. Add a slow-drip test
which enters a blocking read and verifies prompt termination.

On any download failure, unlink the temporary file inside download_source:
the CLI never receives its path and cannot clean it up. The reproduction left
one gtfs-*.zip behind. Cover HTTP failure, oversize, timeout and interrupted
download cleanup. Preserve caller-owned --file archives.

## 3. P2 — effective calendar envelope and freshness precedence

`backend/app/services/transit_import.py:645-657`
`backend/app/services/transit_data.py:140-151`

The envelope uses raw calendar endpoints whenever any weekday is enabled,
and ignores removal exceptions. It is not the effective service envelope.
Reproductions with one referenced service:

- Mondays only, 2026-01-01 through 2026-01-10: current result Jan 1..10;
  the only effective date is Jan 5.
- Mondays only on 2026-01-06 (Tuesday): accepted despite zero service dates.
- Monday 2026-01-05 only, removed by an exception: still accepted despite
  zero service dates.

Derive actual first/last effective dates after weekdays and both exception
types, with bounded work; reject a feed with no effective referenced service
dates. Preserve gaps: an envelope does not mean service on every date.

Freshness returns unknown for missing/future Last-Modified before checking
the calendar. Reproduction: an envelope ending 2025-12-31, checked today,
Last-Modified=None or +2 days -> unknown instead of stale. Known stale
evidence must take precedence over unknown metadata. Test these combinations.

## 4. P2 — archive validation and streaming do not match the handoff

`backend/app/services/transit_import.py:273-353,501-556`

stop_times.txt is read entirely into bytes, decoded into another full string
and wrapped in StringIO. Stream it through a bounded reader; do not retain
several full copies of a file allowed to reach 100 MiB. Enforce actual
uncompressed byte counts, not only central-directory metadata. Validate CRC
for all archive members within those bounds, including ignored shapes.

Reproductions:

- Corrupted CRC in shapes.txt is accepted because the member is never read.
- Corrupted CRC in stops.txt escapes as BadZipFile rather than FeedError;
  the CLI catches only FeedError around parsing and prints a traceback.
- Duplicate stop_id headers in stop_times.txt are accepted. A non-existent
  stop in the first column is silently hidden by a valid second column.

Normalize malformed ZIP/CSV/decode failures into the documented invalid-feed
outcome, reject duplicate headers consistently, and use strict CSV parsing.
Validate non-negative stop_sequence and stored location_type values. The
route-type validator currently accepts every integer 100..1700, including
undefined 333; use the actual supported codes from the handoff's reference.
Align validated string lengths with PostgreSQL columns so --validate-only
does not approve values which fail only when persisted.

Fix the tests too: test_archive_safety_limits leaves MAX_ENTRIES=2 set for
its later row/cell assertions, so those assertions never reach those limits.
Use independent fixtures/patch contexts and assert the actual failure reason.
Cover CRC, stream limits, duplicate headers and CLI exit/error output.

## 5. P2 — PostgreSQL tests will silently skip in CI too

`backend/tests/test_transit_postgres.py:79-118`
`.github/workflows/ci.yml` backend job

The backend job has no PostgreSQL service or TRANSIT_TEST_DATABASE_URL.
Other jobs have PostgreSQL but do not run this Python test file, and their
database is estihub_dev rather than the test suite's default estihub_test.
Nothing currently makes the reported integration gap close in CI.

Owner scope extension for this fix: add a dedicated disposable PostgreSQL
test database/service to CI and run the integration tests with an explicit
TRANSIT_TEST_DATABASE_URL. When this URL is explicitly configured, connection
or setup failures must fail, not skip. Default local absence may still skip.
Use isolated test storage; the fixture currently deletes every transit row
in whichever database the variable points to. Ensure the tests cannot clean
an ordinary application database by mistake.

Exercise real overlapping lock/activation paths, including first import and
an existing good generation, with bounded waits and thread cleanup. Report
local skips and CI configuration separately from an actual successful CI run.
Do not push merely to obtain a green badge without owner authorization.

## 6. P2 — attribution claims have no retained supporting evidence

`backend/app/services/transit_import.py:51-57`
`docs/TRANSIT-DATA-LICENSE.md`

The new persisted credit adds "Maa- ja Ruumiamet via transport.tallinn.ee".
The retained GTFS evidence in DATA-SOURCES names Tallinn and the distribution;
it does not identify Maa- ja Ruumiamet as its author/licensor. The importer
docstring also calls this an In-AKS distribution, apparently carried over
from the address module. Do not guess the licensor or mix these providers.

Use credit supported by retained source metadata and record the exact
evidence. Keep unresolved provenance explicit if fresh verification is
unavailable; do not attribute authorship to the address provider by analogy.
Keep the existing separate-data CC BY-SA handling and release-review gate.
Correct docs saying every response already carries transit credit: there is
no transit HTTP endpoint yet. DATA-SOURCES also still recommends adding a
parser library immediately below its new stdlib implementation paragraph.

## Delivery and validation

- Fix only these M08 concerns and the explicitly permitted CI wiring. No M09,
  no application/frontend feature expansion and no unrelated dictionary edits.
- Add targeted regressions, run the full backend suite and frontend build/lint.
  Run isolated PostgreSQL checks if available; accurately state if not.
- Keep CLI failures concise: SQLAlchemy exception strings can include SQL
  parameters/whole records; report safe categories instead of dumping them.
  Distinguish an unavailable database from actual lock contention, and report
  superseded/conflicting import outcomes consistently with the handoff's
  nonzero failure convention. Add real CLI coverage for the documented exits.
- Update the delivered docs and add TODO journal/Notes insertions describing
  exact checks and remaining verification gaps. Correct the test count in a
  new entry; preserve history and unrelated changes. Separate fix commit,
  then stop for Codex review.
