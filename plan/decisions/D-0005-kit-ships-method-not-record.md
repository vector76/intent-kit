---
id: D-0005
date: 2026-11-23
status: active
from: [I-0003, I-0004, I-0006]
replaces: D-0004
---
# The kit ships as kit/; a project gets the method, cited setup and linked rules

**Decision:**
- **What ships.** The kit is the `kit/` folder: philosophy, onboarding guide, bootstrap
  script, templates and tests. The rest of this repository is the record of developing
  the kit, and nothing from it reaches a project. A new project's intent log, decisions
  and lessons start empty.
- **Onboarding answers.** The owner's answers are not captured as intent entries.
  `intent-kit.json` cites them under `"sources"` by session and message timestamp
  (`tools/kit.py cite`), so the exact words stay findable in the record. The project's
  I-0001 is the owner's first words about the project itself. A change to the setup asked
  for later is captured as intent like anything else, and cited by its I- id.
- **Rules.** The rules generated from the config go into their own file,
  `METHOD-RULES.md`. The project's `CLAUDE.md` stays its own and holds one short section
  ending in an `@METHOD-RULES.md` import line. `render` moves an older inlined section
  out.

**Why:** The owner expected the kit to be projected documents: how-to instructions,
recipes and scripts linked into `CLAUDE.md`, not a record dropped into the project. They
found it strange to start a project's intent with record-keeping answers, or its lessons
with the kit's own bugs (I-0006). The config and the generated rules from D-0004 stay;
what changes is where the answers are cited and where the rules live.

**Alternatives considered:** keeping onboarding answers as I-0001 (D-0004); inlining the
rules in `CLAUDE.md` between markers (D-0004).

**Revisit if:** citing setup answers by session timestamp proves fragile, for example if
the record isn't available where someone needs to check a choice.
