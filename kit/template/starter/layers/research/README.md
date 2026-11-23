# Research

What is known outside this project: science, prior work, parts, costs and prices. One
note per topic: `N-0001-short-name.md`, created with
`python {{TOOLS}}/to_main.py research --slug short-name --file draft.md`. Unlike intent, a
note can be corrected when it's wrong (git keeps the history).

Rules:
- Every factual claim has a source a reader can check (paper, DOI, datasheet, URL).
  Never invent a citation. If a claim comes from general knowledge and hasn't been
  checked, mark it *unverified*.
- Separate what the source says from what it might mean for this project. The second
  part is interpretation, and labelled as such.
- A note doesn't decide anything. It feeds decisions (D-) and experiments (E-).

Template:

```
---
id: {ID}
date: YYYY-MM-DD
topic: short phrase
for: [I-xxxx, R-xxx]   # the question or tension it informs
---
# <topic>

**Summary:** a few sentences.
**What's known:** claims, each with its source.
**What it might mean here:** interpretation, labelled.
**Open:** what this note couldn't settle.
**Sources:** full list.
```
