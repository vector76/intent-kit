---
id: D-0008
date: 2026-11-23
status: active
from: [I-0008, I-0004]
---
# The record's remote is set up by one command, and its URL stays out of the project

**Decision:** Onboarding asks whether the record gets a remote: an existing private
repository, a new one, or none for now. `tools/kit.py record [--remote URL]` does the
setup, and the bootstrap runs it (`--record-remote`).
- If `record/` doesn't exist, it's created as its own git repository.
- If the remote is empty, the record is pushed to it and tracks it.
- If the remote already holds the record, it's checked out. That is also how a fresh
  clone of the project gets its record back.
- If both sides hold records with unrelated histories, nothing is merged; it says how.

A new remote must be private. Either the owner creates it, or the agent runs
`gh repo create --private` once the owner has said yes to that repository. The URL is
kept only in `record/.git/config`, not in `intent-kit.json`. Until `record/` is a
repository, the hooks copy nothing and say so at session start. Before this, they would
fill a plain folder that later got in the way of checking the record out.

**Why:** The owner asked to be prompted for the record's remote, with creating a new
one allowed (I-0008). A record can have a remote (I-0004). Keeping the URL out of the
project's files means a publishable project doesn't reveal where its private record
lives.

**Alternatives considered:** storing the URL in the config so a fresh clone needs no
input (it would be visible to anyone who can read the project); having the kit create
the repository itself through a host's API (it would tie the kit to one host and act
without the owner seeing the command).

**Revisit if:** fresh clones become common enough that typing the URL is a burden. A
confidential project could then keep the URL in its config.
