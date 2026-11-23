#!/usr/bin/env python3
"""Find secrets that have reached the private record, remind the owner, and scrub them
when the owner asks.

  python tools/record_secrets.py                 list what's been found and not dealt with
  python tools/record_secrets.py scan [--full]   look again: new transcript text, or all of it
  python tools/record_secrets.py ignore ID [ID ...]
                                                 not a secret (or one the owner accepts): stop
                                                 reminding
  python tools/record_secrets.py scrub ID [ID ...] [--sources]
                                                 redact them from the record's files and rewrite
                                                 the record's history so no commit holds them;
                                                 --sources also redacts Claude Code's own
                                                 transcript copies (all but this session's)

A finding is shown by its ID, kind, a masked preview and the files it's in, never in full,
so dealing with it doesn't copy it into another transcript. Detection looks for known key
formats, private keys, passwords in URLs and secret-looking values assigned to names like
`password` or `api_key`. It misses secrets in other forms, and flags some things that
aren't secrets: that's what `ignore` is for.

The hooks scan new transcript text as it's copied. While anything found is open, each
session start tells the agent, which tells the owner. A turn that adds a new finding also
shows the owner a warning. Scrubbing rewrites the record's history, so it's done only when
the owner asks. It can't undo a leak: a secret that reached a remote, or anywhere else,
should be revoked or changed as well.

Kept in record/ and committed there: redactions.txt and secrets-ignored.txt, which hold
SHA-256 hashes, not the secrets. The scan's progress and findings stay in record/.git/.

Managed by intent-kit.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import RECORD, SESSIONS, git, transcript_dirs  # noqa: E402

STATE = RECORD / ".git" / "intent-kit-secrets.json"
REDACTED = RECORD / "redactions.txt"
IGNORED = RECORD / "secrets-ignored.txt"
Q = r"(?:\\?[\"'])?"  # an optional quote, maybe JSON-escaped
DETECTORS = [  # kind, pattern, group holding the secret, needs a random-looking value
    ("private key", r"-----BEGIN [A-Z0-9 ]{0,40}PRIVATE KEY-----[\s\S]{20,10000}?-----END [A-Z0-9 ]{0,40}PRIVATE KEY-----",
     0, False),
    ("AWS access key", r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", 0, False),
    ("GitHub token", r"\b(?:gh[pousr]_[A-Za-z0-9]{36,255}|github_pat_[A-Za-z0-9_]{40,255})", 0, False),
    ("GitLab token", r"\bglpat-[A-Za-z0-9_-]{20,255}", 0, False),
    ("Slack token", r"\bxox[abposr]-[A-Za-z0-9-]{10,255}", 0, False),
    ("Stripe key", r"\b[rs]k_live_[A-Za-z0-9]{20,255}", 0, False),
    ("Anthropic key", r"\bsk-ant-[A-Za-z0-9_-]{20,255}", 0, False),
    ("API key (sk-)", r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{32,255}", 0, False),
    ("Google API key", r"\bAIza[0-9A-Za-z_-]{35}", 0, False),
    ("JWT", r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", 0, False),
    ("password in a URL", r"\b[a-z][a-z0-9+.-]{1,20}://[^\s/:@\"'\\]{1,64}:([^\s/@\"'\\]{6,128})@", 1, True),
    ("assigned secret", r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?key|auth[_-]?token|token)" + Q
     + r"\s*[:=]\s*" + Q + r"([A-Za-z0-9_\-+/=!#$%^&*.~]{12,128})", 1, True),
]
COMPILED = [(k, re.compile(p), g, r) for k, p, g, r in DETECTORS]
PLACEHOLDERS = ("example", "xxxx", "your", "placeholder", "changeme", "dummy", "redacted", "****")


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def random_looking(s: str) -> bool:
    if any(p in s.lower() for p in PLACEHOLDERS):
        return False
    if not (re.search(r"[A-Za-z]", s) and re.search(r"\d", s)):
        return False
    counts = {c: s.count(c) for c in set(s)}
    entropy = -sum(n / len(s) * math.log2(n / len(s)) for n in counts.values())
    return entropy >= 3.0


def find(text: str):
    """(kind, secret, start, end) for each likely secret in text, without overlaps."""
    hits = []
    for kind, rx, group, needs_random in COMPILED:
        for m in rx.finditer(text):
            s = m.group(group)
            if s and (not needs_random or random_looking(s)):
                hits.append((m.start(group), m.end(group), kind, s))
    hits.sort(key=lambda h: (h[0], -(h[1] - h[0])))
    out, last = [], -1
    for start, end, kind, s in hits:
        if start >= last:
            out.append((kind, s, start, end))
            last = end
    return out


def mask(kind: str, s: str) -> str:
    if kind == "private key":
        return f"{s.split('-----')[1][:40]} ({len(s)} chars)"
    return f"{s[:4]}... ({len(s)} chars)"


def tag(h: str) -> str:
    return f"[REDACTED:{h[:12]}]"


def hashes(path: Path) -> set[str]:
    try:
        return {ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()}
    except OSError:
        return set()


def redact(text: str, targets: set[str]) -> tuple[str, int]:
    """Replace every detected secret whose hash is in targets. Used when copying transcripts."""
    if not targets:
        return text, 0
    n = 0
    for kind, s, start, end in reversed(find(text)):
        h = sha(s)
        if h in targets:
            text = text[:start] + tag(h) + text[end:]
            n += 1
    return text, n


# --- scanning ------------------------------------------------------------------------

def load_state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"scanned": {}, "found": {}}


def save_state(state: dict):
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")


def record_files():
    for base in (SESSIONS, RECORD / "notes"):
        if base.is_dir():
            yield from (p for p in base.rglob("*") if p.is_file())


def scan(full: bool = False) -> list[str]:
    """Scan new text in the record's files. Returns the hashes of open findings that are new."""
    if not (RECORD / ".git").is_dir():
        return []
    state = load_state()
    if full:
        state["scanned"] = {}
    done = hashes(REDACTED) | hashes(IGNORED)
    new = []
    for p in record_files():
        rel = p.relative_to(RECORD).as_posix()
        size = p.stat().st_size
        seen = state["scanned"].get(rel, 0)
        if size == seen:
            continue
        start = max(0, seen - 16384) if size > seen else 0  # overlap, in case a secret spans the old end
        with p.open("rb") as f:
            f.seek(start)
            text = f.read().decode("utf-8", errors="replace")
        for kind, s, _, _ in find(text):
            h = sha(s)
            entry = state["found"].setdefault(h, {"kind": kind, "preview": mask(kind, s), "where": []})
            if rel not in entry["where"]:
                entry["where"].append(rel)
                if h not in done and len(entry["where"]) == 1:
                    new.append(h)
        state["scanned"][rel] = size
    save_state(state)
    return new


def open_findings(state: dict | None = None) -> dict:
    state = state or load_state()
    done = hashes(REDACTED) | hashes(IGNORED)
    return {h: f for h, f in state["found"].items() if h not in done}


def reminder() -> str | None:
    n = len(open_findings())
    if not n:
        return None
    return (f"intent-kit: the private record holds {n} possible secret(s) that haven't been dealt with. "
            "Tell the owner. `python tools/record_secrets.py` lists them, masked. Scrub or ignore them only "
            "when the owner asks, and suggest revoking any real one.")


def resolve(ids: list[str], state: dict) -> list[str]:
    out = []
    for i in ids:
        match = [h for h in state["found"] if h.startswith(i.lower())]
        if len(match) != 1:
            sys.exit(f"record_secrets: {i!r} matches {len(match)} findings; use the ID from the list")
        out.append(match[0])
    return out


def add_hashes(path: Path, new: list[str]):
    have = hashes(path)
    path.write_text("".join(f"{h}\n" for h in sorted(have | set(new))), encoding="utf-8", newline="\n")


def commit(message: str, *paths: str):
    git("add", "--", *paths, cwd=RECORD)
    if git("diff", "--cached", "--quiet", "--", *paths, cwd=RECORD).returncode != 0:
        git("commit", "-q", "-m", message, "--", *paths, cwd=RECORD, check=True)


# --- scrubbing -----------------------------------------------------------------------

def gitb(*args, input: bytes | None = None) -> bytes:
    r = subprocess.run(["git", "-C", str(RECORD), *args], input=input, capture_output=True)
    if r.returncode != 0:
        sys.exit(f"record_secrets: FAILED: git {' '.join(args)}: {r.stderr.decode(errors='replace').strip()}")
    return r.stdout


def rewrite_history(literals: dict[bytes, bytes]) -> int:
    """Rewrite every branch and tag so no blob holds any of the literals. Returns commits changed."""
    blobs, trees, commits = {}, {}, {}

    def blob(h: str) -> str:
        if h not in blobs:
            data = gitb("cat-file", "blob", h)
            new = data
            for secret, replacement in literals.items():
                new = new.replace(secret, replacement)
            blobs[h] = h if new == data else gitb("hash-object", "-w", "--stdin", input=new).decode().strip()
        return blobs[h]

    def tree(h: str) -> str:
        if h not in trees:
            out, changed = [], False
            for e in gitb("ls-tree", "-z", h).split(b"\0"):
                if not e:
                    continue
                meta, name = e.split(b"\t", 1)
                mode, typ, old = meta.split(b" ")
                new = {b"tree": tree, b"blob": blob}.get(typ, lambda x: x)(old.decode())
                changed |= new != old.decode()
                out.append(mode + b" " + typ + b" " + new.encode() + b"\t" + name)
            trees[h] = gitb("mktree", "-z", input=b"\0".join(out) + b"\0").decode().strip() if changed else h
        return trees[h]

    revs = gitb("rev-list", "--reverse", "--topo-order", "--branches", "--tags").decode().split()
    n = 0
    for c in revs:
        raw = gitb("cat-file", "commit", c)
        head, _, msg = raw.partition(b"\n\n")
        lines = head.split(b"\n")
        old_tree = lines[0].split()[1].decode()
        parents = [ln.split()[1].decode() for ln in lines if ln.startswith(b"parent ")]
        new_tree, new_parents = tree(old_tree), [commits.get(p, p) for p in parents]
        if new_tree == old_tree and new_parents == parents:
            commits[c] = c
            continue
        keep, skip = [], False
        for ln in lines[1:]:
            if ln.startswith(b"parent "):
                continue
            if ln.startswith((b"gpgsig", b"mergetag")):  # signatures no longer match
                skip = True
                continue
            if skip and ln.startswith(b" "):
                continue
            skip = False
            keep.append(ln)
        body = b"\n".join([b"tree " + new_tree.encode()] + [b"parent " + p.encode() for p in new_parents] + keep)
        commits[c] = gitb("hash-object", "-t", "commit", "-w", "--stdin", input=body + b"\n\n" + msg).decode().strip()
        n += 1
    for line in gitb("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags").decode().splitlines():
        ref, old = line.split()
        if commits.get(old, old) != old:
            gitb("update-ref", ref, commits[old], old)
    return n


def scrub(ids: list[str], sources: bool):
    state = load_state()
    targets = resolve(ids, state)
    # everything in the record committed first, so the working files can be reset to the rewritten history
    git("add", "-A", cwd=RECORD)
    if git("diff", "--cached", "--quiet", cwd=RECORD).returncode != 0:
        git("commit", "-q", "-m", "Record before scrubbing", cwd=RECORD, check=True)
    literals = {}  # the secrets as they appear in files: found again, kept in memory only
    for p in record_files():
        for kind, s, _, _ in find(p.read_bytes().decode("utf-8", errors="replace")):
            h = sha(s)
            if h in targets:
                literals[s.encode("utf-8")] = tag(h).encode()
    missing = [h[:12] for h in targets if tag(h).encode() not in literals.values()]
    if missing:
        print(f"record_secrets: not in the record's current files, so not scrubbed from its history: "
              f"{', '.join(missing)}")
    changed = rewrite_history(literals) if literals else 0
    if changed:
        git("reset", "-q", "--hard", cwd=RECORD, check=True)
    add_hashes(REDACTED, targets)
    commit(f"Redact {len(targets)} secret(s)", REDACTED.name)
    git("reflog", "expire", "--expire=now", "--all", cwd=RECORD)
    git("gc", "-q", "--prune=now", cwd=RECORD)
    for p in record_files():
        state["scanned"][p.relative_to(RECORD).as_posix()] = p.stat().st_size
    save_state(state)
    print(f"record_secrets: scrubbed {len(targets)} secret(s); {changed} commit(s) of the record rewritten")
    if git("remote", cwd=RECORD).stdout.strip():
        print("record_secrets: record/ has a remote, which still holds the old history. To replace it there, "
              "push with git -C record push --force-with-lease, and re-clone any other copies. Until then "
              "this clone keeps the old objects too (its remote-tracking refs point to them).")
    if sources:
        current = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
        fixed, skipped = 0, []
        for d in transcript_dirs():
            for p in [*d.glob("*.jsonl"), *(f for f in d.rglob("*") if f.is_file() and f.suffix != ".jsonl")]:
                if current and current in p.as_posix():
                    if p.suffix == ".jsonl" and p.parent == d:
                        skipped.append(p.name)
                    continue
                data = p.read_bytes()
                new = data
                for secret, replacement in literals.items():
                    new = new.replace(secret, replacement)
                if new != data:
                    p.write_bytes(new)
                    fixed += 1
            for p in d.rglob("*.jsonl"):
                if p.parent != d and not (current and current in p.as_posix()):
                    data = p.read_bytes()
                    new = data
                    for secret, replacement in literals.items():
                        new = new.replace(secret, replacement)
                    if new != data:
                        p.write_bytes(new)
                        fixed += 1
        print(f"record_secrets: redacted {fixed} of Claude Code's own transcript file(s)")
        if skipped:
            print("record_secrets: this session's own transcript is still being written, so it wasn't touched. "
                  "The record's copy of it is redacted as it's copied. Run scrub --sources again from a later "
                  "session to clean Claude Code's copy.")
    print("record_secrets: scrubbing doesn't undo exposure. If a secret was real, revoke or change it.")


def show():
    state = load_state()
    found = open_findings(state)
    if not found:
        print("record_secrets: nothing open")
        return
    print(f"{len(found)} possible secret(s) in the record (masked):")
    for h, f in sorted(found.items(), key=lambda x: x[1]["where"][0]):
        where = ", ".join(f["where"][:3]) + (f" and {len(f['where']) - 3} more" if len(f["where"]) > 3 else "")
        print(f"  {h[:12]}  {f['kind']:<18} {f['preview']:<24} {where}")
    print("Ask the owner: scrub ID ... (rewrites the record's history) or ignore ID ... (not a secret).")


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "list"
    if not (RECORD / ".git").is_dir():
        sys.exit("record_secrets: record/ isn't set up (python tools/kit.py record)")
    if cmd == "list":
        show()
    elif cmd == "scan":
        scan(full="--full" in args)
        show()
    elif cmd == "ignore" and args[1:]:
        state = load_state()
        add_hashes(IGNORED, resolve(args[1:], state))
        commit("Mark possible secret(s) as not secret", IGNORED.name)
        show()
    elif cmd == "scrub" and [a for a in args[1:] if a != "--sources"]:
        scrub([a for a in args[1:] if a != "--sources"], "--sources" in args)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
