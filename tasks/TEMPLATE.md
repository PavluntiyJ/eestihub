# T## — <short imperative title>

**Read first:** `docs/CONTEXT.md` (<the sections that actually bind this task>).
**Dependencies:** <task ids, or none>. **Role:** <Backend | Frontend | Full-stack>.
**Branch:** work in `main` (or a feature branch if the orchestrator says so).
**Runs in parallel with:** <task ids> — stay inside "Files you own".
**Blocks:** <task ids that must wait for this one>.

## Context

Why this task exists, in the reader's terms. If it fixes an audit finding,
quote the finding ID and the evidence — a worker who understands the
defect makes better calls than one following steps.

State any decision that is already made and is not up for debate here
(for example: "CONTEXT §5 has already been corrected; implement it as
written, do not re-derive it").

## Steps

1. **Named step.** What to do and, where it is not obvious, why. Any
   figure that comes from the outside world (a tax rate, a fee, a
   threshold) must be verified against a primary source at implementation
   time and recorded with its URL and retrieval date — if no primary
   source states it, stop and record the blocker in `TODO.md` rather than
   inventing a number.
2. ...

## Non-goals

- The adjacent things a reasonable worker might otherwise pull in.
- The work that belongs to a parallel or later task, named by id.
- Anything deliberately deferred, so it reads as a decision rather than
  an oversight.

## Files you own

The explicit list. This is binding: other tasks may be running in
parallel, and overlaps are resolved here rather than left to merge.
If a fix seems to require a file outside the list, write it into
"Notes for the orchestrator" instead of reaching for it.

## Documentation impact

**Mandatory section — do not delete it, and do not leave it as "none"
without having checked.** A task that changes behaviour usually makes
some sentence elsewhere in the repo untrue, and documentation nobody
owns is documentation that silently rots.

The orchestrator fills in what this task is expected to falsify:

- `docs/CONTEXT.md` — **orchestrator-only**. Never edit it. If your work
  changes or adds an API contract, say so explicitly in your journal
  entry so it can be reviewed into §5.
- `README.md` — <either "no impact", or the specific claims that stop
  being true, and whether you or the orchestrator updates them>. Check
  at least: the feature list, the test counts, the structure tree, the
  getting-started commands, and the disclaimer.
- `docs/DEPLOY.md` — <impact, if the task touches deploy, env vars,
  start commands or CI>.
- Anything else that states a fact about the system: `AGENTS.md`, task
  briefs, `render.yaml` comments, module docstrings.

Before you hand off, re-read every statement above and confirm it is
still true of the code you just wrote. Whatever you cannot fix inside
"Files you own", report in "Notes for the orchestrator" — naming the
file and the sentence, not just "docs need updating".

## Acceptance criteria

- [ ] <the checks that must pass, each one observable — a command, a
      status code, a figure, a route table — not a feeling>
- [ ] `cd backend && pytest` green / `cd frontend && npm run build`
      passes; no `any`.
- [ ] Every statement listed under "Documentation impact" is either
      updated or reported in "Notes for the orchestrator".
- [ ] `git diff` touches no file outside "Files you own".

## Verification

- The exact commands you ran, and what you looked at in the output.
- Commits: `type(scope): message` — conventional commits, English.

## On completion

Set T## to `[R]` in `TODO.md` + a journal entry: date · model · what was
done · how it was verified. Name any API-contract addition explicitly for
the orchestrator's CONTEXT §5 update, and list any documentation you
could not update yourself.
