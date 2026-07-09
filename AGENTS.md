# AGENTS.md — rules for AI workers (opencode)

You are a worker on the EstiHub project. Work is directed by the
orchestrator (Tech Lead) through task files. Your duties:

1. **Before any work**, read `docs/CONTEXT.md` in full — it defines the
   stack, repo structure, code rules, API contracts and i18n
   requirements. They are mandatory.
2. Execute **only** the task assigned to you (a `tasks/T##-*.md` file).
   The brief is self-contained: goal, steps, explicit non-goals,
   acceptance criteria.
3. Before handing off, run every check in the acceptance criteria and
   make sure they pass.
4. When done, update `TODO.md`: set your task's status to `[R]`, put
   your model name in the "Worker" column, and add a journal entry at
   the top: date · model · what was done · how it was verified.
5. Questions, blockers and out-of-scope findings go to the
   "Notes for the orchestrator" section in `TODO.md`. Do not fix other
   people's code and do not expand scope.

Forbidden:
- editing `docs/CONTEXT.md`, `CLAUDE.md`, `AGENTS.md` or files in `tasks/`;
- setting the `[x]` status (only the orchestrator does, after review);
- changing the stack, folder structure or API contracts;
- committing `.env`, `node_modules` or build artifacts.

Commits: English, conventional commits (`feat:`, `chore:`, `fix:`),
one meaningful commit per task (or several logical ones).

All project documentation (docs, task briefs, TODO board and journal)
is written in English.
