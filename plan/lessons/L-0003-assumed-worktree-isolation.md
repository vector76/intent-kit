---
id: L-0003
date: 2026-11-23
sessions: []
commits: []
tags: [worktrees, process, inherited]
---
# Threads assumed worktree isolation they didn't have

**What happened:** In an earlier project, threads launched by an agent were expected to
get their own worktree and branch, but ran in the main checkout. Two agents then shared
one working tree. A `git add -A` by one could sweep up the other's files, and the
session file both wrote could name the wrong session in commit trailers.

**Root cause:** An unchecked assumption about the tool that launched the threads. It
happened twice: the first fix rested on a second unchecked assumption.

**How to avoid it:** Built into the generated CLAUDE.md rules: check `git worktree list`
before relying on isolation, and in a shared checkout commit only your own paths
(`git commit -- <paths>`). The tools no longer depend on it: `to_main.py` finds whichever
checkout has main, or commits to main directly when none does. The commit hook prefers
`CLAUDE_CODE_SESSION_ID` over the shared session file.
