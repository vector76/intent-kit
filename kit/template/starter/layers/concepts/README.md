# Concepts

Candidate designs or hypotheses: coherent combinations of choices that might meet the
vision. One file per concept: `C-0001-short-name.md`, created with
`python {{TOOLS}}/to_main.py concept --slug short-name --file draft.md`.

A concept is a hypothesis, not a decision. Several can be kept alive at once, and none
is promoted to a decision (D-) without the owner saying so. A concept is revised as
research and experiments come in (git keeps the history), or set aside with a one-line
reason; it isn't deleted.

Template:

```
---
id: {ID}
date: YYYY-MM-DD
status: candidate | set-aside
from: [I-xxxx, N-xxxx, E-xxxx]
---
# <one-line description>

**Sketch:**
**Against the requirements:** where it lands, and with what confidence.
**Enabling milestones:** the gates on the path, in order, each one testable.
**First test:** the cheapest experiment that would teach the most.
**Biggest risks:**
```
