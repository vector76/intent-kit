---
id: D-0006
date: 2026-11-23
status: active
from: [I-0007, I-0002]
---
# Syncing a branch after to_main is opt-in

**Decision:** When `to_main.py` (or the extractor) commits an entry or copies documents
to main, the branch the session is on is no longer synced automatically. It prints that
the branch doesn't have the change yet and doesn't need it, because numbers come from
main. Branches sync at session start, as the rules already say, or whenever someone runs
`tools/sync.py`. A project can turn the old behavior back on with
`"sync_after_to_main": true` (`--sync-after-to-main` at bootstrap).

**Why:** Under linear landing, syncing rebases the branch, rewriting its history. Claude
Code worktrees are often pushed or have pull requests open, and those would then need
force-pushing after every capture. Under merge landing, it would add a merge commit for
every capture. The owner chose opt-in (I-0007). Worktree-awareness (I-0002) holds either
way: the numbering is done on main.

**Alternatives considered:** always sync (the earlier behavior); sync only when the
branch has no upstream.

**Revisit if:** agents keep missing entries or vision changes that are on main but not
yet on their branch.
