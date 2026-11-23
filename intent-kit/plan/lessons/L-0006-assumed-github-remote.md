---
id: L-0006
date: 2026-11-23
sessions: [6d25e113-df43-4d10-b870-5932ea9ad280]
commits: [e6f2d87]
tags: [onboarding, record, assumptions]
---
# Onboarding assumed the record's remote was on GitHub, and treated "no remote" as unfinished

**What happened:** Kit 0.4.0 (commit e6f2d87, D-0008) told the onboarding agent to
create a new record remote with `gh repo create --private` and to check it with
`gh repo view`. That is GitHub's command-line tool. It offered "none for now" as the
alternative, and `kit.py check` noted on every run that the record "exists only on this
machine". The owner pointed out that a remote doesn't always mean GitHub, that they
don't want the `gh` tool used, and that keeping the record local is a real choice,
somewhat safer for privacy (I-0009).

**Root cause:** The most common host was taken for the only one, and a host-specific tool
was added without being asked for. Having a remote was treated as the finished state,
and local only as a gap to close, when for a private record it's arguably the safer
default.

**How to avoid it:** Fixed in 0.4.1 (D-0009). Use plain git, which works with any server,
and use no host's own tool unless the owner names it. When offering choices, present the
conservative one (less exposure, fewer moving parts) as a full option, not as something
to grow out of. Don't add checks that nag the owner about a choice they made on purpose.
