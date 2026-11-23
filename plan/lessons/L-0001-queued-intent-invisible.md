---
id: L-0001
date: 2026-11-23
sessions: []
commits: []
tags: [intent-capture, tooling, inherited]
---
# Intent sent while the agent was working was invisible to the extractor

**What happened:** In two earlier projects, the owner sent a substantial statement of
intent while a turn was running. The message was absorbed into that turn, and the
extractor's `--list` didn't show it. Had the session ended there, the words would have
been missing from the intent log.

**Root cause:** A missing check in the capture tool. Claude Code writes a message typed
mid-turn as a `queue-operation` record (`operation: "enqueue"`), not as a `user` record.
When it's absorbed into the running turn, no `user` record is ever written. The tool only
read `user` records.

**How to avoid it:** Built in. The extractor reads `enqueue` records too, and drops the
queued copy when a `user` record has the same text. The rule in CLAUDE.md: before ending a
session, re-run `--list` and check that every unmarked message is captured or isn't
intent. `--list` now marks captured messages with `*`, so the count is easy to check.
