# Experiments

Work that answers an open question or checks a requirement. This is how reality feeds
back into intent: a build, a bench test, a calculation, a model or a simulation. One
folder per experiment, `E-0001-short-name/README.md` plus any code, data and figures.
Start one with `python {{TOOLS}}/to_main.py experiment --slug short-name --file draft.md`:
that puts its README on main with the next number, and the work then continues on your
branch. Template:

```
---
id: {ID}
date_started: YYYY-MM-DD
status: planned | running | done | abandoned
kind: build | test | calculation | model | simulation
question_from: [I-xxxx, R-xxx]   # the tension or requirement it answers
---
# <question>

**Question:**
**Method:** what was done, and how it was checked.
**Result:** numbers and observations.
**What it changed:** effect on the vision, requirements or decisions. If it changes
the intent, the owner confirms and it becomes a new intent entry.
```
