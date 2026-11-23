"""Shared helpers for the intent-kit tools.

Managed by intent-kit: `bootstrap.py upgrade` replaces this file. Project-specific
choices live in the kit folder's config.json, not here.

Everything the kit adds to a project lives in one folder (intent-kit/ unless the project
chose another name at setup): the tools, the commit hook, the config, the intent log, the
vision and plan, the optional layers and the private record. Only CLAUDE.md's import line
and the hooks in .claude/settings.json are outside it. The folder is wherever these tools
are: <repo>/<kit folder>/tools/.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
KIT_HOME = TOOLS.parent  # this checkout's kit folder


def _git(args, cwd, input=None, env=None):
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                          encoding="utf-8", input=input, env=env)


def _toplevel(path: Path) -> Path | None:
    r = _git(["rev-parse", "--show-toplevel"], path)
    out = r.stdout.strip()
    return Path(out).resolve() if r.returncode == 0 and out else None


REPO = _toplevel(TOOLS) or KIT_HOME.parent  # this checkout (may be a worktree)
try:
    KIT_DIR = KIT_HOME.relative_to(REPO).as_posix()  # the kit folder, relative to the repo: "intent-kit"
except ValueError:
    KIT_DIR = "intent-kit"


def kp(rel: str) -> str:
    """A repo-relative path inside the kit folder."""
    return f"{KIT_DIR}/{rel}"


CONFIG_NAME = kp("config.json")
TOOLS_REL = kp("tools")


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
    "python": "python",                # the command the hooks and rules use to run the tools
    "visibility": "confidential",      # confidential | publishable
    "layers": [],                      # research, concepts, experiments
    "stances": [],                     # wide-search, forward-plausibility
    "landing": "linear",               # linear (rebase + fast-forward) | merge
    "push_on_land": True,
    "sync_after_to_main": False,       # sync the branch after to_main commits to main
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
RECORD = MAIN / KIT_DIR / "record"
SESSIONS = RECORD / "sessions"
KNOWN_DIRS = RECORD / "transcript-dirs.txt"       # transcript folders seen by the hooks
STATE = REPO / KIT_DIR / ".state"                  # ignored, per checkout
CURRENT = STATE / "current-session"                # each worktree tags its own commits
TURNS = STATE / "record-turns"                     # per-session turn counts


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


def record_problem(need_repo: bool = True) -> str | None:
    """None if record/ is safely private (ignored by this repo, not tracked by it) and, with
    need_repo, set up as its own git repository."""
    rec = kp("record")
    if git("ls-files", "--", rec, cwd=MAIN).stdout.strip():
        return f"{rec}/ is tracked by the project repository"
    if git("check-ignore", "-q", "--no-index", kp("record/sessions/x.jsonl"), cwd=MAIN).returncode != 0:
        return f"{rec}/ is not ignored ({KIT_DIR}/.gitignore should list /record/)"
    if need_repo and not (RECORD / ".git").exists():
        return (f"{rec}/ is not set up as its own git repository (in the main checkout: "
                f"python {TOOLS_REL}/kit.py record [--remote <private url>])")
    return None


# --- who is working here --------------------------------------------------------------
# Each person names themself once per clone; it's kept in the clone's own git config
# (shared by its worktrees, never committed). A session is one person's: it can't be
# shared or handed over, so the person set up where it runs is its author.

NAME_KEY = "intent-kit.name"


def my_name() -> str:
    """The name of the person working in this clone, or "" if they haven't been asked yet."""
    return git("config", "--get", NAME_KEY, cwd=MAIN).stdout.strip()


def set_my_name(name: str):
    git("config", "--local", NAME_KEY, name.strip(), cwd=MAIN, check=True)


def suggested_name() -> str:
    """A default for "what shall I call you?": Claude Code's name for its signed-in account,
    else git's user.name. Never an email address."""
    try:
        acct = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8")).get("oauthAccount") or {}
        for key in ("displayName", "fullName"):
            v = str(acct.get(key) or "").strip()
            if v and "@" not in v:
                return v
    except (OSError, ValueError, AttributeError):
        pass
    v = git("config", "--get", "user.name", cwd=MAIN).stdout.strip()
    return v if "@" not in v else ""


def author_file(transcript_copy: Path) -> Path:
    """The record's note of whose session a copied transcript is: <date>_<id>.author."""
    return transcript_copy.with_suffix(".author")


def session_author(sid: str) -> str:
    """Whose session this was, as the record noted it when the session was copied ("" if unknown)."""
    for p in SESSIONS.glob(f"*{sid}.author"):
        return p.read_text(encoding="utf-8").strip()
    return ""


def is_local_transcript(path: Path) -> bool:
    """True for a transcript in this machine's Claude folders (so the person set up here wrote it),
    False for one known only from the record (it may be anyone's)."""
    try:
        Path(path).resolve().relative_to(projects_root().resolve())
        return True
    except ValueError:
        return False


def yaml_str(s: str) -> str:
    """A front-matter value: bare when safe, else quoted."""
    return s if re.fullmatch(r"[A-Za-z0-9][\w .'()-]*", s) and not s.endswith(" ") else json.dumps(s)


MIN_PYTHON = (3, 10)


def python_version(cmd: str) -> tuple[int, int] | None:
    """The (major, minor) version that `cmd` runs, or None if it doesn't run."""
    try:
        argv = [cmd] if Path(cmd).is_file() else cmd.split()  # "python3", "py -3" or a full path
        r = subprocess.run([*argv, "-c", "import sys; print(*sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            major, minor = (int(x) for x in r.stdout.split()[:2])
            return major, minor
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
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
    """kind: (repo-relative folder, ID prefix, digits, entry is a folder)."""
    cfg = cfg or CFG
    k = dict(BASE_KINDS)
    for layer in cfg.get("layers", []):
        if layer in LAYER_KINDS:
            name, spec = LAYER_KINDS[layer]
            k[name] = spec
    return {name: (kp(folder), *rest) for name, (folder, *rest) in k.items()}


DOCS = [kp("intent/vision.md"), kp("plan"), CONFIG_NAME, "CLAUDE.md", kp("METHOD-RULES.md")]  # current-view documents


def is_doc(path: str) -> bool:
    return any(path == d or path.startswith(d + "/") for d in DOCS)


def main_tree_files(folder: str) -> list[str]:
    """Paths under `folder` on the main branch (empty if main or the folder doesn't exist yet)."""
    r = git("ls-tree", "-r", "--name-only", TARGET, "--", folder, cwd=MAIN)
    return r.stdout.split() if r.returncode == 0 else []


def main_file_text(path: str) -> str:
    r = git("show", f"{TARGET}:{path}", cwd=MAIN)
    return r.stdout if r.returncode == 0 else ""
