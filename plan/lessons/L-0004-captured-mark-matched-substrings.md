---
id: L-0004
date: 2026-11-23
sessions: [6d25e113-df43-4d10-b870-5932ea9ad280]
commits: []
tags: [intent-capture, tooling]
---
# The "already captured" mark matched substrings, so short messages looked captured

**What happened:** In kit 0.1.0 and 0.2.0, `extract_human_messages.py --list` marked a
message `*` if its text appeared anywhere in any intent entry. A short message such as
"Yes" would be marked captured whenever an entry contained those words, even though it
wasn't. Found in a review of the kit before any project relied on it. A test showed the
old code marking a lone "Yes" as captured.

**Root cause:** A loose check. The mark is the safety net for "every message has an
entry", and it was an approximation that errs in the unsafe direction.

**How to avoid it:** Fixed in 0.3.0. Entries are split back into their messages, and a
message is marked only if it matches one whole. A message that itself contains a line of
`---` can fail to match and show unmarked, which errs on the safe side. Checks that
guard completeness should fail toward "look at this", never toward "done".
