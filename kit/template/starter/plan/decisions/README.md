# Decisions

One file per decision: `D-0001-short-name.md`, created with
`python {{TOOLS}}/to_main.py decision --slug short-name --file draft.md` (the draft uses
`{ID}` for the number). A decision is replaced by a new one (`replaces: D-0003`) rather
than edited into something else. Template:

```
---
id: {ID}
date: YYYY-MM-DD
status: active | replaced-by D-xxxx
from: [I-xxxx, E-xxxx, N-xxxx, R-xxx]
agreed_by: [<who agreed to it>]
---
# <decision>

**Decision:** one or two sentences.
**Why:** the reasons, citing the IDs above.
**Alternatives considered:** briefly.
**Revisit if:** what would make this wrong.
```
