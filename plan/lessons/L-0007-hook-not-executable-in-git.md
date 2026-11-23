---
id: L-0007
date: 2026-11-23
sessions: [6d25e113-df43-4d10-b870-5932ea9ad280]
commits: [3f42524]
tags: [hooks, cross-platform, bootstrap]
---
# The commit hook was committed without its executable bit, so other systems would skip it

**What happened:** Every kit version up to 0.4.1 committed `.githooks/prepare-commit-msg`
as mode `100644`: in the kit, in every project it bootstrapped, and in a project on the earlier machinery. The
bootstrap did make the file executable on disk. But on Windows git doesn't record the
executable bit (`core.fileMode` is false), so git's copy wasn't executable. On macOS or
Linux, git skips a hook without the bit, so commits there would get no `Session:` trailer.
At most a hint would show, easy to miss. `kit.py check` only checked that the file
existed. It was found in a review of the kit, before any project was cloned to another
system. Fixed in 0.5.0.

**Root cause:** The setup was only ever run and tested on Windows, where the problem
can't show. The check tested for the file, not for whether it would run.

**How to avoid it:** Set the executable bit in git's copy (`git add --chmod=+x` or
`git update-index --chmod=+x`), whatever the machine. Have checks test that a thing will
actually work, not only that it exists. Treat "tested on one platform" as untested on the
others, and say so.
