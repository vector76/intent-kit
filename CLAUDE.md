# intent-kit — working rules for agents

A reusable setup that bootstraps new or existing projects into traceable, intent-driven development: verbatim intent, current-view projections, and a private session record.

## Project rules

- **The kit is `kit/`, and only `kit/` ships** (I-0006). Everything a project receives
  comes from `kit/template/` and `kit/PHILOSOPHY.md`. This repo's own intent, plan,
  decisions, lessons and record are about developing the kit, and must never be copied
  into a project. A test checks that a new project's log and lessons start empty.
- **Change the tools in `kit/template/managed/`, never in `intent-kit/tools/`.** That's
  an installed copy: after editing, run `python kit/bootstrap.py upgrade . --apply`.
- **`kit/` is the product; `intent-kit/` is this repo's own use of it** (its intent, plan,
  tools and record), the same folder every project gets.
  Bump `kit/VERSION` when what a project gets changes.
- **Run the tests** after any change to the kit:
  `python -m unittest discover -s kit/tests -v`.
- **Keep what ships free of any project's specifics.** No names, subjects or details from
  the projects the kit came from go in `kit/`: some of those projects are confidential.

## How this project keeps its record

This project follows the intent-kit method. Everything the kit adds is in `intent-kit/`: `intent-kit/METHOD.md` explains the method, and the working rules below are generated into `intent-kit/METHOD-RULES.md` from `intent-kit/config.json`. Project-specific rules belong in this file, not that one.

@intent-kit/METHOD-RULES.md
