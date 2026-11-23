---
id: D-0013
date: 2026-11-23
status: active
from: [I-0014, I-0013]
agreed_by: [Jamie Kawabata]
---
# Intent entries quote the agent's questions only when the words need them

**Decision:** The extractor takes `--question "<text>"` and `--question-file <file>`,
each repeatable.
- **Placement:** each question goes after the human's words, under a comment saying it
  is the agent's words and not intent, as a blockquote.
- **Verbatim check:** each question must appear, whitespace aside, in the agent's own
  text in the main conversation before the answer (not a subagent's). Anything else is
  refused, so the block stays verbatim.
- **Matching:** the block is ignored when checking whether a message is already
  captured, so the entry still holds only the human's words.
- **The rules make it a judgment call:**
  - Add a question only when the words can't be understood without it.
  - Add none when they make sense on their own.
  - Quote only the questions the words depend on, never more.

**Why:** The owner wants questions included only when they're necessary. A message may be
mostly intent that stands on its own, so including them isn't a hard rule (I-0014).
Answers like those in I-0013 can't be read without what was asked, and the record that
holds the question may be on another machine.

**Alternatives considered:**
- Always include the agent's whole preceding message: it's long, and mostly not what the
  words answer.
- Let the agent write a summary of the question: it would be the agent's paraphrase,
  where the log holds only quoted words.
- Leave context to the record: it may not be reachable from another clone.

**Revisit if:** entries collect questions they don't need, or answers still can't be
read on their own.
