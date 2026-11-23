---
id: D-0014
date: 2026-11-23
status: active
from: [I-0018, I-0019]
agreed_by: [Jamie Kawabata]
---
# Everything the kit adds lives in one folder, intent-kit/ by default

**Decision:** A project gets one kit folder, named at setup with `--kit-dir` and
`intent-kit` by default. It holds:
- the tools
- the commit hook (`githooks/`, with `core.hooksPath` pointing there)
- `config.json`, which replaces the root `intent-kit.json`
- `METHOD.md` and the generated `METHOD-RULES.md`
- the intent log, vision and plan, and the optional layers
- the private record (`record/`, still its own repo and ignored)
- local state (`.state/`, which replaces the files kept in `.claude/`) and drafts (`out/`)
- a `README.md` saying what the folder is
- its own `.gitignore` and `.gitattributes`, which git applies only inside the folder

Outside the folder:
- **`CLAUDE.md`** gets one import line, `@intent-kit/METHOD-RULES.md`. It has to stay at
  the root, because Claude Code reads it there.
- **`.claude/settings.json`** gets the capture hooks. It has to stay where it is, because
  Claude Code reads it there.
- **A new project** also gets a short root `README.md` pointing into the folder.
- **An existing project's root files** aren't touched, `.gitignore` and `.gitattributes`
  included.

The tools find the folder from their own location, so its name isn't stored anywhere it
could drift. The `tools_dir` setting is gone, because the root no longer holds anything
the kit's files could collide with. The layout counts as 1.0.0: the tag moves to it
(I-0019).

**Why:** The owner expects clients not to like a kit that clutters the root, collides
with folders of the same name and mixes its documents with other stacks' (I-0018). The
project's own documents (intent, vision, plan) go in the folder too (I-0019, answer 2).
The name is configurable, with intent-kit as the default (I-0019, answer 1), because
"intent-kit" may not be the kit's final name.

**Alternatives considered:**
- A hidden `.intent-kit/`: tidier, but people are meant to read the vision and the log.
- Keeping `intent/` and `plan/` at the root: the owner chose the folder for them as well.
- Calling the layout 2.0.0: the owner chose to move the 1.0.0 tag (I-0019, answer 3).

**Revisit if:** projects need the kit's documents somewhere other tools expect, or the
kit gets its final name.
