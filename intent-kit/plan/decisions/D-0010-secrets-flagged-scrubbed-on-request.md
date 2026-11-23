---
id: D-0010
date: 2026-11-23
status: active
from: [I-0010, I-0009]
---
# Secrets in the record: flagged by the hooks, scrubbed only when the owner asks

**Decision:** A managed tool, `tools/record_secrets.py`, looks for likely secrets in the
record. It checks for:
- known key formats (cloud, code-hosting, chat and payment keys, JWTs)
- private key blocks
- passwords in URLs
- random-looking values assigned to names like `password` or `api_key`

How it works:
- **The hooks scan only new text** as transcripts are copied.
- **A turn that adds a finding shows the owner a warning**, through the Stop hook's
  `systemMessage`.
- **While findings are open**, each session start tells the agent, which tells the owner.
  `kit.py check` notes them too.
- **Findings are shown only by ID, kind, a masked preview and location**, never in full,
  so handling one doesn't copy it into another transcript.
- **`ignore <id>`** marks a finding as not a secret.
- **`scrub <id>`**, run only when the owner asks, redacts it from the record's files.
  It also rewrites every branch and tag of the record so no commit holds it, then expires
  the reflog and prunes the old objects. `--sources` also redacts Claude Code's own
  transcript copies of sessions that have ended.
- **Copies made after a scrub are redacted on the way in**, so the secret doesn't come
  back on the next copy.
- **The record keeps only SHA-256 hashes of scrubbed and ignored findings**
  (`redactions.txt`, `secrets-ignored.txt`), never the secrets.
- **Scrubbing never pushes.** If the record has a remote, the owner force-pushes the
  rewritten history themselves. Pushing stays manual, which the owner accepted (I-0010).
- **Every scrub says that a real secret should also be revoked.**

**Why:** The owner asked for a way to remind them, and to scrub history on request, if
secrets appear (I-0010). The record keeps everything a session touched, and a remote puts
it on a server (I-0009).

**Alternatives considered:**
- Depend on `git filter-repo`: an extra install, and it needs the secret's text as input.
- Redact everything at copy time, without asking: it would silently change the record and
  mangle false positives.
- Scan the project repository too: rewriting a shared, pushed project history is a
  different and riskier job, and it's left out.

**Revisit if:** the detectors miss a kind of secret the owner uses, or flag too much to be
useful. Also if the owner wants the project repository covered.
