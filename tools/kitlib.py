"""Shared helpers for the intent-kit tools.

Managed by intent-kit: `bootstrap.py upgrade` replaces this file. Project-specific
choices live in intent-kit.json, not here.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
CONFIG_NAME = "intent-kit.json"


def _git(args, cwd, input=None, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          encoding="utf-8", input=input, env=env)


def _toplevel(path: Path) -> Path | None:
    r = _git(["rev-parse", "--show-toplevel"], path)
    out = r.stdout.strip()
    return Path(out).resolve() if r.returncode == 0 and out else None


REPO = _toplevel(TOOLS) or TOOLS.parent  # this checkout (may be a worktree)


def _main_checkout() -> Path:
    """The main checkout, even when running inside a git worktree."""
    r = _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], REPO)
    if r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve().parent
    return REPO


MAIN = _main_checkout()

DEFAULTS = {
    "kit_version": "0.0.0",
    "project": "",
    "summary": "",
    "main_branch": "main",
    "tools_dir": "tools",
    "visibility": "confidential",      # confidential | publishable
    "layers": [],                      # research, concepts, experiments
    "stances": [],                     # wide-search, forward-plausibility
    "landing": "linear",               # linear (rebase + fast-forward) | merge
    "push_on_land": True,
    "agents": "claude-only",           # claude-only | any
    "backplane": False,
    "record_commit_every": 10,
    "not_human_prefixes": [],
    "sources": {},                     # setting -> [intent ids that set it]
}


def load_config(root: Path | None = None) -> dict:
    for base in ([root] if root else [REPO, MAIN]):
        p = Path(base) / CONFIG_NAME
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            return {**DEFAULTS, **data}
    return dict(DEFAULTS)


CFG = load_config()
TARGET = CFG["main_branch"]
RECORD = MAIN / "record"
SESSIONS = RECORD / "sessions"
KNOWN_DIRS = RECORD / "transcript-dirs.txt"       # transcript folders seen by the hooks
CURRENT = REPO / ".claude" / "current-session"     # per checkout: each worktree tags its own commits
TURNS = REPO / ".claude" / "record-turns"          # per-session turn counts


def git(*args, cwd=None, check=False, input=None, env=None, tool="kit"):
    r = _git(args, cwd or REPO, input=input, env=env)
    if check and r.returncode != 0:
        sys.exit(f"{tool}: FAILED: git {' '.join(args)}:\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def out(*args, cwd=None, tool="kit") -> str:
    return git(*args, cwd=cwd, check=True, tool=tool).stdout.strip()


def current_branch(cwd=None) -> str:
    return git("symbolic-ref", "--short", "-q", "HEAD", cwd=cwd).stdout.strip()


def session_id() -> str:
    """This session's id: Claude Code's own variable, else the checkout's session file."""
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID", "").strip()
    if sid:
        return sid
    return CURRENT.read_text(encoding="utf-8").strip() if CURRENT.is_file() else ""


def with_trailer(msg: str) -> str:
    sid = session_id()
    if sid and f"Session: {sid}" not in msg:
        msg = msg.rstrip() + f"\n\nSession: {sid}\n"
    return msg


# --- worktrees and transcripts -------------------------------------------------------

def worktrees() -> list[dict]:
    """Every checkout of this repo: [{'path': Path, 'branch': 'main' | None}]."""
    wts, cur = [], None
    for line in git("worktree", "list", "--porcelain", cwd=MAIN).stdout.splitlines():
        if line.startswith("worktree "):
            cur = {"path": Path(line[len("worktree "):]).resolve(), "branch": None}
            wts.append(cur)
        elif line.startswith("branch refs/heads/") and cur is not None:
            cur["branch"] = line[len("branch refs/heads/"):]
    return wts


def checkout_of(branch: str) -> Path | None:
    """The checkout that has `branch` checked out, if any."""
    for wt in worktrees():
        if wt["branch"] == branch:
            return wt["path"]
    return None


def mangle(p) -> str:
    """Claude Code's name for a working folder's transcript directory."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(p))


def projects_root() -> Path:
    return Path.home() / ".claude" / "projects"


def known_dir_names() -> set[str]:
    try:
        return {ln.strip() for ln in KNOWN_DIRS.read_text(encoding="utf-8").splitlines() if ln.strip()}
    except OSError:
        return set()


def remember_transcript_dir(transcript: Path):
    """Note the folder a session's transcript lives in, so a sweep finds it again even
    after its worktree is gone or its path was too long to guess."""
    name = transcript.parent.name
    if not name or not RECORD.is_dir() or name in known_dir_names():
        return
    with KNOWN_DIRS.open("a", encoding="utf-8", newline="\n") as f:
        f.write(name + "\n")


def transcript_dirs() -> list[Path]:
    """Every folder holding this project's transcripts: the main checkout's, every current
    worktree's, worktrees inside the repo that are gone (<main>--...), and any folder the
    hooks have seen. Not a sibling project's (myproj2/)."""
    root = projects_root()
    if not root.is_dir():
        return []
    main = mangle(MAIN)
    names = {main} | {mangle(wt["path"]) for wt in worktrees()} | known_dir_names()
    dirs = {root / n for n in names}
    dirs |= {d for d in root.glob(main + "--*") if d.is_dir()}
    return sorted(d for d in dirs if d.is_dir())


def find_transcript(sid: str) -> Path | None:
    for d in transcript_dirs():
        if (d / f"{sid}.jsonl").is_file():
            return d / f"{sid}.jsonl"
    return None


def record_problem() -> str | None:
    """None if record/ is safely private: ignored by this repo and not tracked by it."""
    if git("ls-files", "--", "record", cwd=MAIN).stdout.strip():
        return "record/ is tracked by the project repository"
    if git("check-ignore", "-q", "--no-index", "record/sessions/x.jsonl", cwd=MAIN).returncode != 0:
        return "record/ is not ignored by the project's .gitignore"
    return None


# --- numbered entries and current-view documents -------------------------------------

BASE_KINDS = {  # kind: (folder, ID prefix, digits, entry is a folder)
    "intent": ("intent/log", "I", 4, False),
    "decision": ("plan/decisions", "D", 4, False),
    "lesson": ("plan/lessons", "L", 4, False),
}
LAYER_KINDS = {  # layer name in the config: kind
    "research": ("research", ("research", "N", 4, False)),
    "concepts": ("concept", ("concepts", "C", 4, False)),
    "experiments": ("experiment", ("experiments", "E", 4, True)),
}


def kinds(cfg=None) -> dict:
    cfg = cfg or CFG
    k = dict(BASE_KINDS)
    for layer in cfg.get("layers", []):
        if layer in LAYER_KINDS:
            name, spec = LAYER_KINDS[layer]
            k[name] = spec
    return k


DOCS = ["intent/vision.md", "plan", CONFIG_NAME, "CLAUDE.md"]  # current-view documents


def is_doc(path: str) -> bool:
    return any(path == d or path.startswith(d + "/") for d in DOCS)


def main_tree_files(folder: str) -> list[str]:
    """Paths under `folder` on the main branch (empty if main or the folder doesn't exist yet)."""
    r = git("ls-tree", "-r", "--name-only", TARGET, "--", folder, cwd=MAIN)
    return r.stdout.split() if r.returncode == 0 else []


def main_file_text(path: str) -> str:
    r = git("show", f"{TARGET}:{path}", cwd=MAIN)
    return r.stdout if r.returncode == 0 else ""
