---
id: D-0003
date: 2026-11-23
status: active
from: [I-0005]
---
# Intent about the method shares the one intent log, unmarked

**Decision:** The owner's intent about how a project is run and recorded goes into the
same `intent/log/` as intent about the project, with no kind marker and no separate log.
The vision projects the project intent. The configuration (`intent-kit.json` and the
generated part of CLAUDE.md) cites the method intent.

**Why:** The owner chose this (I-0005). If a clean project-only rendering is ever
wanted, it can be produced from the log on request. Owners also mix both kinds in one
message, and a verbatim log can't split a message.

**Alternatives considered:** a `kind:` field on each entry; a separate method log with
its own IDs; recording configuration as decisions only.

**Revisit if:** method entries crowd the log enough to make projecting the vision hard.
