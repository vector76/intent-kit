# intent-kit

A reusable setup for **traceable, intent-driven projects** run with AI agents. The
owner's intent is captured verbatim and projected into a current vision and plan. Every
commit traces back to the session that made it, and every session's raw transcript is
kept in a separate private record. Reality corrects the intent through experiments,
and the projections are redrawn.

- [PHILOSOPHY.md](PHILOSOPHY.md): the method and why it works the way it does. A copy
  goes into each project as `METHOD.md`.
- [ONBOARDING.md](ONBOARDING.md): what the agent does to bring a project in, new or
  existing. This is where to start.
- `kit/bootstrap.py`: sets a project up (`init`) and brings its kit-managed files up to
  date later (`upgrade`).
- `kit/template/`: the files a project gets. `managed/` holds the tools and commit hook,
  which the kit owns and `upgrade` replaces. `starter/` holds the documents, which are
  written once and then belong to the project.
- `kit/tests/`: end-to-end tests (`python -m unittest discover -s kit/tests -v`).

## Quick start

In a Claude Code session in the target project's folder:

> Set this project up with the intent kit at `<path to intent-kit>`; read its ONBOARDING.md.

The agent looks at the project, asks a few questions (visibility, layers, landing
policy and so on), shows a dry run, bootstraps it, and captures the conversation as the
project's first intent entries.

## What a project gets

```
CLAUDE.md               working rules; a section generated from intent-kit.json
intent-kit.json         the project's choices, citing the intent entries that set them
METHOD.md               this kit's PHILOSOPHY.md
intent/log/             the owner's words, verbatim, append-only (I-0001)
intent/vision.md        the current view, synthesized from the log
plan/                   requirements (R-), decisions (D-), lessons (L-)
research/ concepts/ experiments/    optional layers (N-, C-, E-)
tools/                  capture, extract, to_main, sync, land, kit (check / render)
.githooks/              Session: trailer on every commit
.claude/settings.json   hooks that copy each session's transcript into record/
record/                 a separate private git repo, ignored by the project
```

## This repository

The kit is itself run by its own method: see [intent/vision.md](intent/vision.md) and
[intent/log/](intent/log/). The tools in `tools/` here are an installed copy of
`kit/template/managed/tools/`. Edit the kit's copy, then run
`python kit/bootstrap.py upgrade . --apply`.
