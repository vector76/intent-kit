---
id: D-0004
date: 2026-11-23
status: replaced-by D-0005
from: [I-0003, I-0004]
---
# Onboarding choices live in intent-kit.json and generate part of CLAUDE.md

**Decision:** Onboarding is a conversation in the project's first session. The owner's
answers are captured verbatim as intent, and the choices are written to a committed
`intent-kit.json` that cites those entries under `"sources"`. The tools read the config,
and `tools/kit.py render` turns it into a generated section of CLAUDE.md between markers.
The rest of CLAUDE.md is hand-written. `tools/kit.py check` verifies that the repo matches
its config. The kit's managed files (tools, commit hook, METHOD.md) are copied in and kept
current with `bootstrap.py upgrade`.

**Why:** The owner wanted an onboarding phase whose answers the repository respects
(I-0003), and agreed to the shape proposed for it (I-0004: "everything else I think makes
sense").

**Alternatives considered:** a terminal questionnaire (the owner speaks their input, so a
conversation suits better); a git submodule or installed package for the tools (copying
keeps each project self-contained, and `upgrade` shows the drift).

**Revisit if:** keeping several projects' copies of the tools in step becomes a chore.
