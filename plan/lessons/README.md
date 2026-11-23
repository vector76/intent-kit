# Lessons

Short postmortems, one per mistake: `L-0001-short-name.md`, created with
`python tools/to_main.py lesson --slug short-name --file draft.md`. Agents read these
before related work. Append-only. Template:

```
---
id: {ID}
date: YYYY-MM-DD
sessions: [<session id where it happened>, <session id where it was found>]
commits: [<sha>]
found_by: [<who found the problem: a person, or "agent" in a named session>]
tags: [process, ...]
---
# <what went wrong, in one line>

**What happened:**
**Root cause:** (bad intent? bad projection? bad execution? bad source? missing check?)
**How to avoid it:** a concrete check or rule. If it's a rule, also add it to CLAUDE.md.
```
