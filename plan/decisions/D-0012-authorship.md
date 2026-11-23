---
id: D-0012
date: 2026-11-23
status: active
from: [I-0011, I-0012, I-0013]
agreed_by: [Jamie Kawabata]
---
# Authorship: each clone names its person, each session is one person's, entries say whose

**Decision:**
- **Who works in a clone** is asked once ("what shall I call you?") and kept in that
  clone's git config (`intent-kit.name`), never committed.
  - The suggested name is Claude Code's account name (`displayName`, then `fullName` in
    `~/.claude.json`), else git's `user.name`, never an email address.
  - The bootstrap takes it as `--me`. `kit.py whoami [--set]` shows or sets it.
  - A clone without one is asked at its first session start, and `kit.py check` notes it.
- **Each session in the record gets a note of whose it is**
  (`record/sessions/<date>_<id>.author`). It is written once, when the session is first
  copied with a name set, and never changed, because a session can't be shared or
  handed over (I-0013). The note is committed with the session's own files.
- **Each intent entry has an `author:` header.** The extractor takes the author from the
  session's note in the record or, for a transcript on this machine, from the clone's
  name.
  - `--author` is allowed only when neither is known, and is refused if it differs from
    a known author.
  - Relayed wishes get `--on-behalf-of NAME`. The entry stays the speaker's and counts as
    the speaker's view of what NAME wants (I-0013).
  - A hand-written intent entry gets the clone's name if it has no author.
- **Decisions need `agreed_by:` and lessons need `found_by:`.** `to_main.py` refuses a
  draft without them.
- **Agreeing is a new entry** (I-0012).
- **Requirements and the vision name no one** unless intent differs. The open question
  then names who holds each view (I-0012).
- **Older entries can be attributed with `kit.py attribute NAME --apply`.** It adds only
  the `author:` line, after the owner approves (I-0013, answer 1). The kit's own
  I-0001 to I-0013 were attributed this way.

**Why:** The owner wants every piece of intent traceable to a person, so that people can
find each other when intent conflicts, without proof or signatures (I-0011). Identity
comes from onboarding with an inferred default (I-0012). Relayed intent records both the
speaker and who is claimed, and defaults to non-impersonation (I-0012). The rest settles
the owner's answers in I-0013.

**Alternatives considered:**
- A name in `intent-kit.json`: it's shared, but a name belongs to a person and a clone.
- An `author` trailer on commits: git already records the commit's author, and it's the
  intent that needs attributing.
- A separate attribution file for old entries, leaving the log files untouched: the
  owner chose the header (I-0013).
- Backfilling `agreed_by:` and `found_by:` on existing decisions and lessons: not asked
  for. Who agreed to or found what would be a guess.

**Revisit if:** two people share a name (ignored for now, I-0013), sessions ever do
become shared, or attribution needs to be checkable rather than taken on trust.
