---
id: D-0001
date: 2026-11-23
status: active
from: [I-0002, I-0003]
---
# Numbered entries are sequential and committed to main when created

**Decision:** Intent entries, decisions, lessons and the optional layers' entries get
sequential numbers taken from the main branch, and each is committed to main the moment
it's created, from any checkout: the main checkout, a worktree, or a branch in a single
checkout. Current-view documents (vision, plan, CLAUDE.md, intent-kit.json) are copied
to main as soon as they're edited. Everything else lands by the project's policy.

**Why:** Worktrees are a general fact of life, not only Backplane's (I-0002). Main
handing out the numbers means they never collide. Committing at capture also means
intent from a worktree that never lands still reaches the log. Random IDs (I-0002)
would fix collisions but not stranded intent, and would lose short IDs that are easy
to cite. The owner chose this option (I-0003).

**Alternatives considered:** random IDs, timestamp IDs, provisional IDs renumbered at
landing, random IDs committed to main.

**Revisit if:** committing to main from inside a worktree turns out to fight a tool's own
branch handling, or entries start needing review before they reach main.
