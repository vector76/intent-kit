---
id: D-0002
date: 2026-11-23
status: active
from: [I-0003, I-0004]
---
# The session record is always a separate private repository

**Decision:** `record/` is always its own git repository, ignored by the project
repository. It isn't a configuration choice. It may have its own private remote, so
several people can push and pull the record. The capture hook refuses to copy
transcripts if `record/` isn't ignored or is tracked by the project, and warns the
session.

**Why:** Keeping the record in the project repo is an easy mistake that can leak
transcripts by accident (I-0004). I-0003 had raised an in-repo option, with sessions
following their worktree. The owner reversed that in I-0004.

**Alternatives considered:** a per-project choice between in-repo and separate (I-0003).

**Revisit if:** a project needs its sessions to travel with its branches and can show
the record would never be published with it.
