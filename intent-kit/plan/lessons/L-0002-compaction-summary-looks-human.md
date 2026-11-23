---
id: L-0002
date: 2026-11-23
sessions: [6d25e113-df43-4d10-b870-5932ea9ad280]
commits: []
tags: [intent-capture, tooling]
---
# Compaction summaries look like the owner's messages

**What happened:** While building the kit, a check of real transcripts showed that when
a long session is compacted, the summary Claude Code writes ("This session is being
continued from a previous conversation...") is stored as a `user` record. Its text
doesn't start with `<`, so both earlier extractors would have listed it as a human
message, and it could have been captured as intent. No capture went wrong before it was
found.

**Root cause:** The extractor filtered by text shape (a leading `<`) and two flags
(`isMeta`, `isSidechain`), and trusted every other `user` record to be human. That was a
missing check, not bad intent.

**How to avoid it:** Built in. The extractor also skips records flagged
`isCompactSummary` or `isVisibleInTranscriptOnly`, and the tests cover it. More generally:
when Claude Code adds a new kind of record, check the extractor against a real
transcript.
