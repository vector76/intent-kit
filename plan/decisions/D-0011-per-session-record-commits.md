---
id: D-0011
date: 2026-11-23
status: active
from: [I-0010]
---
# Each session commits only its own files in the record, and retries if git is busy

**Decision:** The Stop and SessionEnd hooks commit only the session's own transcript and
its side folder (`git commit -- <paths>`), not everything in `record/`. The session-start
sync and `capture_session.py --all --commit` still commit everything, as a sweep.

If another commit holds the record's index lock, the hook waits briefly and retries for a
few seconds before giving up. If it gives up, the next commit picks the files up.

The SessionEnd hook gets a 30-second timeout, because Claude Code gives SessionEnd hooks
1.5 seconds by default. `kit.py render` adds the timeout to existing projects, and
`check` reports if it's missing.

**Why:** The owner pointed out that sessions sharing a checkout have distinct session ids,
and so distinct files in the record, and should be able to commit independently (I-0010).
They can, but each git repository has one index, and two commits can't run at the same
moment. Before this, the second commit failed without a message, and one session's commit
swept up the other's files.

**Alternatives considered:** a separate index file per session (`GIT_INDEX_FILE`), which
avoids the lock but still contends for the branch ref; a lock of the kit's own around
record commits.

**Revisit if:** commits are still lost when many sessions run at once.
