---
id: L-0005
date: 2026-11-23
sessions: [6d25e113-df43-4d10-b870-5932ea9ad280]
commits: []
tags: [adoption, bootstrap]
---
# Adopting a repo wrote files that change how git treats its existing work

**What happened:** In kit 0.1.0 and 0.2.0, `bootstrap.py init` on an existing repository
added a `.gitattributes` (`* text=auto eol=lf`) if there was none, and added `/out/` to
`.gitignore`. In a repo with Windows line endings committed, the first can make many
files show as modified. The second would quietly stop new files in a project's own
`out/` folder from being tracked. Found in a review of the kit, before it was used on a
real project.

**Root cause:** "Only add, never overwrite" was treated as enough. Some added files
change how git handles files that are already there.

**How to avoid it:** Fixed in 0.3.0. For an existing repo, the bootstrap suggests these
instead of writing them. A new project still gets both. When adopting, ask of each added
file whether it changes the meaning of existing files, not only whether it overwrites one.
