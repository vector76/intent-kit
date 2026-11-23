---
id: D-0009
date: 2026-11-23
status: active
from: [I-0009, I-0008, I-0004]
replaces: D-0008
---
# The record is local only by default; a remote can be on any git server

**Decision:** Onboarding offers three equal choices for where the record lives:
- **local only**, with no remote (the default);
- an existing private repository on any git server;
- a new private one.

Nothing steers toward a remote. `kit.py check` doesn't note a missing one, and the
bootstrap's dry run says "local only".

A remote is whatever URL `git` accepts: a hosting service, a self-hosted server, an SSH
host or a bare repository on another drive. The kit uses only plain git. If the owner
wants the agent to create a new remote, the agent uses `git init --bare`, locally or over
`ssh`, once the owner has said yes to that exact location. It uses no hosting service's
own tool or API unless the owner asks for that tool. The owner confirms the remote is
private, because no check works on every host.

`tools/kit.py record [--remote URL]` does the setup, as in D-0008:
- If the remote is empty, the record is pushed to it.
- If the remote already holds the record, it's checked out.
- Records with unrelated histories are never merged automatically.

The URL stays in `record/.git/config`, not in the project. On a fresh clone, a local-only
record starts afresh on that machine. Carrying an earlier one over is up to the owner.

**Why:** The owner wants local only as an option, since it's somewhat safer for privacy:
there's no server copy to misconfigure or leak. They don't want the `gh` tool used, and a
remote doesn't mean GitHub (I-0009). The owner asked to be prompted for a remote, with
creating a new one allowed (I-0008). A record can have a remote (I-0004).

**Alternatives considered:**
- Keep D-0008's framing, where no remote meant "none for now" and `check` noted it.
- Support each hosting service's tool.

**Revisit if:** the owner wants a specific host's tooling supported.
