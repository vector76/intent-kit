# intent-kit

A reusable setup for **traceable, intent-driven projects** run with AI agents. The
owner's intent is captured verbatim and projected into a current vision and plan. Every
commit traces back to the session that made it, and every session's raw transcript is
kept in a separate private record. Reality corrects the intent through experiments,
and the projections are redrawn.

This folder is the whole kit: everything a project gets comes from here.

- [PHILOSOPHY.md](PHILOSOPHY.md): the method and why it works the way it does. A copy
  goes into each project as `METHOD.md`.
- [ONBOARDING.md](ONBOARDING.md): what the agent does to bring a project in, new or
  existing. This is where to start.
- `bootstrap.py`: sets a project up (`init`) and brings its kit-managed files up to date
  later (`upgrade`).
- `template/managed/`: the tools and commit hook, which the kit owns and `upgrade`
  replaces.
- `template/starter/`: the documents a project starts with (READMEs, vision and
  requirements skeletons). They're written once and then belong to the project.
- `tests/`: end-to-end tests (`python -m unittest discover -s tests -v`).

## Quick start

Needs git and Python 3.10 or later; onboarding checks for both.

In a Claude Code session in the target project's folder:

> Set this project up with the intent kit at `<path to this folder>`; read its ONBOARDING.md.

The agent looks at the project, asks a few questions (visibility, layers, landing policy
and so on), shows a dry run and bootstraps it. It cites your answers from the project's
config. The project's intent log starts with what you say about the project itself.

## What a project gets

```
CLAUDE.md               the project's own; gains one short section ending in @METHOD-RULES.md
METHOD-RULES.md         working rules, generated from intent-kit.json (imported by CLAUDE.md)
METHOD.md               this kit's PHILOSOPHY.md
intent-kit.json         the project's choices, citing what set them
intent/log/             the owner's words, verbatim, append-only (I-0001), empty to start
intent/vision.md        the current view, synthesized from the log
plan/                   requirements (R-), decisions (D-), lessons (L-), empty to start
research/ concepts/ experiments/    optional layers (N-, C-, E-)
tools/                  capture, extract, to_main, sync, land, kit (check / render / cite / record),
                        record_secrets (flag secrets in the record; scrub on request)
.githooks/              Session: trailer on every commit
.claude/settings.json   hooks that copy each session's transcript into record/
record/                 a separate private git repo, ignored by the project, with its own
                        private remote if the owner wants one
```
