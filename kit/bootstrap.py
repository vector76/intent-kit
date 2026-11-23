#!/usr/bin/env python3
"""Set a project up with intent-kit, or bring its kit-managed files up to date.

  python bootstrap.py init <dir> --name NAME [--summary TEXT] [choices...] [--dry-run]
  python bootstrap.py upgrade <dir> [--kit-dir NAME] [--apply]

Everything the kit adds goes in one folder, intent-kit/ unless --kit-dir names another:
the tools, the commit hook, the config, the intent log, the vision and plan, the
optional layers and the private record, with their own .gitignore and .gitattributes.
Outside it, only CLAUDE.md gains an import line and .claude/settings.json gains the
capture hooks; a new project also gets a README.md.

init works on a new folder (it runs `git init`) or an existing repository (it adopts
it). It only adds: existing files are never overwritten. CLAUDE.md and
.claude/settings.json are merged into; anything that can't be merged safely stops the
run before a single file is written, with a list of what's in the way.

Choices (see ONBOARDING.md for what each means; the agent asks the owner):
  --visibility confidential|publishable      default confidential
  --layers research,concepts,experiments     default none
  --stances wide-search,forward-plausibility default none
  --landing linear|merge                     default linear
  --no-push                                  don't push main to remotes when landing
  --sync-after-to-main                       bring the branch up to date after each entry or docs copy
  --agents claude-only|any                   default claude-only
  --backplane                                the project uses Backplane
  --main-branch NAME                         default: current branch, or main
  --kit-dir NAME                             the folder the kit's files go in; default intent-kit
  --python CMD                               how the hooks run Python (python3, python, py -3 or a
                                             path); default: the first of those that runs 3.10+
  --record-remote URL                        a private git repo for record/: an empty one gets the
                                             record pushed to it; one holding the record is checked out
  --config answers.json                      the same choices as a JSON object
  --me NAME                                  what to call the person setting it up (asked at onboarding;
                                             default: Claude Code's account name, else git's user.name).
                                             Kept in this clone's git config, not committed

upgrade compares the project's kit-managed files (the tools, the commit hook, METHOD.md
and the folder's .gitignore) with this kit and shows what differs; --apply replaces them, adds any
missing starter files (say, for a layer turned on since), records the kit version
and re-renders METHOD-RULES.md (moving an older inlined rules section out of
CLAUDE.md). Project content is never touched.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
MANAGED = KIT / "template" / "managed"
STARTER = KIT / "template" / "starter"
PHILOSOPHY = KIT / "PHILOSOPHY.md"
VERSION = (KIT / "VERSION").read_text(encoding="utf-8").strip()
TOOL_FILES = ["kitlib.py", "capture_session.py", "extract_human_messages.py", "to_main.py",
              "sync.py", "land.py", "kit.py", "record_secrets.py"]
LAYERS = {"research": "research", "concepts": "concepts", "experiments": "experiments"}
STANCES = {"wide-search", "forward-plausibility"}
DEFAULT_KIT_DIR = "intent-kit"
HOOK_EVENTS = ["SessionStart", "Stop", "SessionEnd"]
SESSION_END_TIMEOUT = 30  # seconds; Claude Code gives SessionEnd hooks 1.5 s unless told otherwise
ADDED_SETTINGS = {"sync_after_to_main": False, "python": "python"}  # what older kits' hooks ran
MIN_PYTHON = (3, 10)
QUIET = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}


def python_version(cmd: str):
    """(major, minor) that `cmd` runs, or None. The same check as tools/kitlib.py."""
    try:
        argv = [cmd] if Path(cmd).is_file() else cmd.split()
        r = subprocess.run([*argv, "-c", "import sys; print(*sys.version_info[:2])"],
                           capture_output=True, text=True, timeout=30)
        if r.returncode == 0:
            major, minor = (int(x) for x in r.stdout.split()[:2])
            return major, minor
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return None


def find_python() -> str | None:
    """The first usual Python command that runs a new enough Python here. On Windows, plain
    `python3` is often the Store's placeholder, so it's tried last."""
    names = ["python", "py -3", "python3"] if os.name == "nt" else ["python3", "python"]
    for name in names:
        v = python_version(name)
        if v and v >= MIN_PYTHON:
            return name
    return None


def suggested_name() -> str:
    """Claude Code's name for its signed-in account, else git's user.name; never an email address."""
    try:
        acct = json.loads((Path.home() / ".claude.json").read_text(encoding="utf-8")).get("oauthAccount") or {}
        for key in ("displayName", "fullName"):
            v = str(acct.get(key) or "").strip()
            if v and "@" not in v:
                return v
    except (OSError, ValueError, AttributeError):
        pass
    v = subprocess.run(["git", "config", "--get", "user.name"], capture_output=True, text=True).stdout.strip()
    return v if "@" not in v else ""


def git(*args, cwd, check=False, input=None, env=None):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                       encoding="utf-8", input=input, env=env)
    if check and r.returncode != 0:
        sys.exit(f"bootstrap: FAILED: git {' '.join(args)}:\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def hook_path(cfg: dict) -> str:
    return f"{cfg['kit_dir']}/githooks/prepare-commit-msg"


def fill(text: str, cfg: dict) -> str:
    d = cfg["kit_dir"]
    return (text.replace("{{PROJECT}}", cfg["project"])
                .replace("{{SUMMARY}}", cfg.get("summary") or "*(One-paragraph summary to come.)*")
                .replace("{{TOOLS}}", f"{d}/tools")
                .replace("{{KIT}}", d))


def managed_files(cfg: dict) -> dict[str, Path]:
    """Project path -> kit source, for every file the kit owns."""
    d = cfg["kit_dir"]
    m = {f"{d}/tools/{n}": MANAGED / "tools" / n for n in TOOL_FILES}
    m[hook_path(cfg)] = MANAGED / "githooks" / "prepare-commit-msg"
    m[f"{d}/METHOD.md"] = PHILOSOPHY
    m[f"{d}/.gitignore"] = MANAGED / "gitignore"
    return m


def starter_files(cfg: dict) -> dict[str, str]:
    """Project path -> text, for files the kit creates once and the project then owns."""
    d, s = cfg["kit_dir"], {}
    for rel in ["intent/README.md", "intent/vision.md", "plan/requirements.md",
                "plan/decisions/README.md", "plan/lessons/README.md", ".gitattributes"]:
        s[f"{d}/{rel}"] = fill((STARTER / rel).read_text(encoding="utf-8"), cfg)
    for layer in cfg["layers"]:
        s[f"{d}/{LAYERS[layer]}/README.md"] = fill(
            (STARTER / "layers" / layer / "README.md").read_text(encoding="utf-8"), cfg)
    s[f"{d}/README.md"] = kit_readme_text(cfg)
    return s


def readme_text(cfg: dict) -> str:
    """The README of a new project (an existing one keeps its own, or none)."""
    d = cfg["kit_dir"]
    head = "**Confidential. Never publish this repository.**\n\n" if cfg["visibility"] == "confidential" else ""
    return (f"# {cfg['project']}\n\n{head}{cfg.get('summary') or ''}\n\n"
            f"The project's intent, plan and record-keeping are in [`{d}/`]({d}/README.md).\n")


def kit_readme_text(cfg: dict) -> str:
    """The kit folder's own README: what's in it."""
    rows = ["intent/log/       people's words, verbatim, append-only, each naming its author (I-xxxx)",
            "intent/vision.md  current view, synthesized from the log",
            "plan/             requirements (R-), decisions (D-), lessons learned (L-)"]
    if "research" in cfg["layers"]:
        rows.append("research/         what is known outside this project, with sources (N-)")
    if "concepts" in cfg["layers"]:
        rows.append("concepts/         candidate designs and hypotheses (C-)")
    if "experiments" in cfg["layers"]:
        rows.append("experiments/      builds, tests and calculations that answer open questions (E-)")
    rows += ["tools/            record-keeping scripts",
             "githooks/         the hook that adds a Session: trailer to each commit",
             "config.json       how this project is run, citing what set each choice",
             "METHOD-RULES.md   working rules for agents, generated from config.json",
             "record/           raw session transcripts: a separate private repository, ignored"]
    head = "**Confidential. Never publish this repository.**\n\n" if cfg["visibility"] == "confidential" else ""
    return (f"# {cfg['project']}: intent and record\n\n{head}"
            "Everything the intent-kit method keeps for this project, in one folder so it doesn't mix with "
            "the project's own files.\n\n```\n" + "\n".join(rows) + "\n```\n\n"
            "People's intent is recorded verbatim, projected into a current vision and plan, and corrected "
            "by what the work teaches. Commits reference the session that made them by a `Session:` trailer. "
            "See [METHOD.md](METHOD.md).\n")


def claude_text(cfg: dict) -> str:
    return (f"# {cfg['project']} — working rules for agents\n\n"
            f"{cfg.get('summary') or ''}\n\n"
            "## Project rules\n\n*(Project-specific working rules go here.)*\n")


def merged_settings(path: Path, cfg: dict) -> str | None:
    """New settings.json text with the capture hooks added, or None if nothing to add."""
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    cmd = f'{cfg["python"]} "$CLAUDE_PROJECT_DIR/{cfg["kit_dir"]}/tools/capture_session.py"'
    hooks = data.setdefault("hooks", {})
    changed = False
    for ev in HOOK_EVENTS:
        groups = hooks.setdefault(ev, [])
        if not any("capture_session.py" in h.get("command", "") for g in groups for h in g.get("hooks", [])):
            groups.append({"hooks": [{"type": "command", "command": cmd, **({"timeout": SESSION_END_TIMEOUT} if ev == "SessionEnd" else {})}]})
            changed = True
    return json.dumps(data, indent=2) + "\n" if changed else None


def choices(a) -> dict:
    cfg = {}
    if a.config:
        cfg.update(json.loads(Path(a.config).read_text(encoding="utf-8")))
    given = {
        "project": a.name, "summary": a.summary, "visibility": a.visibility, "landing": a.landing,
        "agents": a.agents, "main_branch": a.main_branch, "kit_dir": a.kit_dir,
        "layers": [x for x in a.layers.split(",") if x] if a.layers is not None else None,
        "stances": [x for x in a.stances.split(",") if x] if a.stances is not None else None,
        "push_on_land": False if a.no_push else None, "backplane": True if a.backplane else None,
        "sync_after_to_main": True if a.sync_after_to_main else None,
        "python": a.python,
    }
    cfg.update({k: v for k, v in given.items() if v is not None})
    defaults = {"summary": "", "visibility": "confidential", "layers": [], "stances": [],
                "landing": "linear", "push_on_land": True, "sync_after_to_main": False, "agents": "claude-only",
                "backplane": False, "kit_dir": DEFAULT_KIT_DIR,
                "record_commit_every": 10, "not_human_prefixes": [], "sources": {}}
    cfg = {**defaults, **cfg}
    if cfg["backplane"] and "[Backplane] " not in cfg["not_human_prefixes"]:
        cfg["not_human_prefixes"] = [*cfg["not_human_prefixes"], "[Backplane] "]
    errors = []
    if not cfg.get("project"):
        errors.append("--name is required")
    if cfg["visibility"] not in ("confidential", "publishable"):
        errors.append("--visibility is confidential or publishable")
    if cfg["landing"] not in ("linear", "merge"):
        errors.append("--landing is linear or merge")
    if cfg["agents"] not in ("claude-only", "any"):
        errors.append("--agents is claude-only or any")
    if bad := [x for x in cfg["layers"] if x not in LAYERS]:
        errors.append(f"unknown layers: {', '.join(bad)}")
    if bad := [x for x in cfg["stances"] if x not in STANCES]:
        errors.append(f"unknown stances: {', '.join(bad)}")
    parts = str(cfg["kit_dir"]).replace("\\", "/").strip("/").split("/")
    if not all(re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9._-]*", x) for x in parts):
        errors.append("--kit-dir is a folder name (letters, digits, '.', '_' and '-'), or a path of them")
    cfg["kit_dir"] = "/".join(parts)
    if not cfg.get("python"):
        cfg["python"] = find_python()
        if not cfg["python"]:
            errors.append("no Python 3.10 or later runs here as python3, python or py -3, and the hooks need "
                          "one. Install Python (the owner does this), or pass --python <command or path>")
    else:
        v = python_version(cfg["python"])
        if not v or v < MIN_PYTHON:
            errors.append(f"--python {cfg['python']!r} " + (f"is Python {v[0]}.{v[1]}; the tools need 3.10 or later"
                                                            if v else "doesn't run here"))
    if errors:
        sys.exit("bootstrap: " + "; ".join(errors))
    return cfg


def run_tool(root: Path, cfg: dict, *args) -> int:
    r = subprocess.run([sys.executable, str(root / cfg["kit_dir"] / "tools" / "kit.py"), *args],
                       cwd=str(root), text=True, encoding="utf-8")
    return r.returncode


def init(a):
    root = Path(a.dir).resolve()
    cfg = choices(a)
    is_repo = (root / ".git").exists()
    if is_repo:
        common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=root).stdout.strip()
        if Path(common).resolve() != (root / ".git").resolve():
            sys.exit(f"bootstrap: {root} is a worktree; run this in the main checkout")
        if not cfg.get("main_branch"):
            cfg["main_branch"] = git("symbolic-ref", "--short", "-q", "HEAD", cwd=root).stdout.strip() or "main"
    cfg.setdefault("main_branch", "main")
    cfg["main_branch"] = cfg["main_branch"] or "main"
    d = cfg["kit_dir"]
    hook = hook_path(cfg)
    config_rel = f"{d}/config.json"
    config = {"kit_version": VERSION, **{k: cfg[k] for k in (
        "project", "summary", "main_branch", "python", "visibility", "layers", "stances", "landing",
        "push_on_land", "sync_after_to_main", "agents", "backplane", "record_commit_every", "not_human_prefixes",
        "sources")}}

    # --- what's in the way? nothing is written until this is empty ---
    blockers = []
    if (root / config_rel).exists():
        blockers.append(f"{config_rel} exists: this project is already set up (use `upgrade`)")
    elif (root / d).exists() and any((root / d).iterdir()):
        blockers.append(f"{d}/ already exists and isn't empty; choose another folder for the kit with --kit-dir")
    if is_repo:
        if git("ls-files", "--", d, cwd=root).stdout.strip():
            blockers.append(f"{d}/ holds files tracked by this repository; choose another folder with --kit-dir")
        hp = git("config", "core.hooksPath", cwd=root).stdout.strip()
        if hp and hp != f"{d}/githooks":
            blockers.append(f"core.hooksPath is already {hp!r}; the Session: trailer hook needs {d}/githooks")
        own = root / ".git" / "hooks" / "prepare-commit-msg"
        if own.is_file() and not hp:
            blockers.append(".git/hooks/prepare-commit-msg exists and would stop running; merge it into "
                            f"{d}/githooks/ by hand first")
    remote = a.record_remote
    if remote and git("ls-remote", remote, cwd=root if root.exists() else KIT, env=QUIET).returncode != 0:
        blockers.append(f"can't reach the record remote {remote} (check the URL and that you can read it)")
    settings = root / ".claude" / "settings.json"
    try:
        new_settings = merged_settings(settings, cfg)
    except json.JSONDecodeError:
        blockers.append(".claude/settings.json isn't valid JSON")
        new_settings = None
    if blockers:
        sys.exit("bootstrap: nothing was changed. In the way:\n  " + "\n  ".join(blockers))

    # --- plan ---
    writes = {}  # rel -> text
    for rel, src in managed_files(cfg).items():
        if not (root / rel).exists():
            writes[rel] = src.read_text(encoding="utf-8")
    skipped = []
    for rel, text in starter_files(cfg).items():
        if (root / rel).exists():
            skipped.append(rel)
        else:
            writes[rel] = text
    if not is_repo and not (root / "README.md").exists():
        writes["README.md"] = readme_text(cfg)
    if not (root / "CLAUDE.md").exists():
        writes["CLAUDE.md"] = claude_text(cfg)
    writes[config_rel] = json.dumps(config, indent=2) + "\n"
    if new_settings:
        writes[".claude/settings.json"] = new_settings

    print(f"bootstrap: {'adopting' if is_repo else 'creating'} {root} (kit {VERSION})")
    for rel in sorted(writes):
        verb = "update" if (root / rel).exists() else "add"
        print(f"  {verb:6} {rel}")
    for rel in skipped:
        print(f"  keep   {rel} (exists; left as it is)")
    print(f"  {d}/record/ as its own git repo{' (exists)' if (root / d / 'record' / '.git').exists() else ''}"
          + (f", remote {remote}" if remote else ", local only (no remote)"))
    print(f"  hooks run Python as: {cfg['python']}")
    me = (a.me or "").strip() or suggested_name()
    print(f"  sessions and intent here recorded as: {me}" + ("" if a.me else " (suggested; --me to change)")
          if me else "  sessions and intent here recorded as: nobody yet (pass --me NAME)")
    print(f"  git config core.hooksPath {d}/githooks")
    print(f"  render {d}/METHOD-RULES.md and import it from CLAUDE.md (one @{d}/METHOD-RULES.md line)")
    if a.dry_run:
        print("bootstrap: dry run; nothing was changed")
        return

    # --- do it ---
    root.mkdir(parents=True, exist_ok=True)
    if not is_repo:
        git("init", "-q", "-b", cfg["main_branch"], cwd=root, check=True)
    for rel, text in writes.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8", newline="\n")
        if rel == hook:
            p.chmod(0o755)
    git("config", "core.hooksPath", f"{d}/githooks", cwd=root, check=True)
    if me:
        git("config", "--local", "intent-kit.name", me, cwd=root, check=True)
    if run_tool(root, cfg, "record", *(["--remote", remote] if remote else [])) != 0:
        print("bootstrap: the record isn't fully set up (see above); fix it, then run "
              f"python {d}/tools/kit.py record" + (f" --remote {remote}" if remote else ""))
    run_tool(root, cfg, "render")
    # Windows doesn't record the executable bit, and macOS and Linux skip a hook without it,
    # so git's copy is marked executable whatever this machine is.
    if is_repo:
        git("add", "--chmod=+x", "--", hook, cwd=root, check=True)
        print(f"bootstrap: staged {hook} as executable (git skips a hook that isn't, on macOS and Linux)")
    else:
        git("add", "-A", cwd=root, check=True)
        git("update-index", "--chmod=+x", "--", hook, cwd=root, check=True)
        git("commit", "-q", "-m", f"Set up {cfg['project']} with intent-kit {VERSION}", cwd=root, check=True)
        print(f"bootstrap: committed the scaffold on {cfg['main_branch']}")
    run_tool(root, cfg, "check")
    t = f"{d}/tools"
    print("\nbootstrap: next steps (ONBOARDING.md has the detail):")
    if is_repo:
        print(f"  - review and commit the scaffold on {cfg['main_branch']} (git status)")
        print(f"  - sweep this project's earlier sessions into the record: python {t}/capture_session.py --all --commit")
    if not me:
        print(f"  - ask the owner what to call them, then: python {t}/kit.py whoami --set \"<name>\"")
    print(f"  - cite the owner's onboarding answers in {config_rel} (not as intent): "
          f"python {t}/kit.py cite <session-id> --msg <n> --keys <settings>")
    print(f"  - capture the owner's first words about the project as I-0001: "
          f"python {t}/extract_human_messages.py <session-id> --list")
    print(f"  - write {d}/intent/vision.md from them, then python {t}/to_main.py docs -m \"...\"")


def find_kit_dir(root: Path) -> str | None:
    """The project's kit folder: the one holding config.json and tools/kitlib.py."""
    found = [p.name for p in sorted(root.iterdir()) if p.is_dir()
             and (p / "config.json").is_file() and (p / "tools" / "kitlib.py").is_file()]
    return found[0] if len(found) == 1 else None


def upgrade(a):
    root = Path(a.dir).resolve()
    d = a.kit_dir or find_kit_dir(root)
    if not d:
        sys.exit(f"bootstrap: no kit folder found in {root} (pass --kit-dir, or use `init`)")
    cfg_path = root / d / "config.json"
    if not cfg_path.is_file():
        sys.exit(f"bootstrap: {root} has no {d}/config.json; use `init`")
    cfg = {"layers": [], "project": root.name, "summary": "", "visibility": "confidential",
           **json.loads(cfg_path.read_text(encoding="utf-8")), "kit_dir": d}
    hook = hook_path(cfg)
    changed = []
    for rel, src in managed_files(cfg).items():
        p = root / rel
        new = src.read_text(encoding="utf-8")
        old = p.read_text(encoding="utf-8") if p.is_file() else None
        if old == new:
            continue
        changed.append(rel)
        if old is None:
            print(f"--- {rel}: missing; the kit would add it")
        else:
            diff = difflib.unified_diff(old.splitlines(), new.splitlines(), f"project/{rel}", f"kit/{rel}",
                                        lineterm="", n=2)
            print("\n".join(diff))
    new_starters = [rel for rel in starter_files(cfg) if not (root / rel).exists()]
    for rel in new_starters:
        print(f"--- {rel}: missing starter file; the kit would add it")
    old_version = cfg.get("kit_version", "?")
    mode = git("ls-files", "-s", "--", hook, cwd=root).stdout.split()
    hook_not_x = bool(mode) and mode[0] != "100755"
    if hook_not_x:
        print(f"--- {hook}: tracked as not executable, so git on macOS and Linux skips it; the kit would fix that")
    if not changed and not new_starters and not hook_not_x and old_version == VERSION:
        print(f"bootstrap: {root} is up to date with kit {VERSION}")
        return
    if not a.apply:
        print(f"\nbootstrap: {len(changed)} managed file(s) differ, {len(new_starters)} starter file(s) missing "
              f"(project kit {old_version}, this kit {VERSION}). Run again with --apply to update them.")
        return
    for rel in changed:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(managed_files(cfg)[rel].read_text(encoding="utf-8"), encoding="utf-8", newline="\n")
    starters = starter_files(cfg)
    for rel in new_starters:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(starters[rel], encoding="utf-8", newline="\n")
    if hook_not_x:
        git("update-index", "--chmod=+x", "--", hook, cwd=root, check=True)
        print(f"bootstrap: staged {hook} as executable; commit it")
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    data["kit_version"] = VERSION
    for k, v in ADDED_SETTINGS.items():  # settings added in later kit versions, at their defaults
        data.setdefault(k, v)
    cfg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    run_tool(root, cfg, "render")
    print(f"bootstrap: updated {len(changed) + len(new_starters)} file(s) to kit {VERSION}. Commit the tools "
          f"as usual; publish {d}/config.json, {d}/METHOD-RULES.md and CLAUDE.md with {d}/tools/to_main.py docs.")
    run_tool(root, cfg, "check")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("dir")
    i.add_argument("--name")
    i.add_argument("--summary")
    i.add_argument("--visibility")
    i.add_argument("--layers")
    i.add_argument("--stances")
    i.add_argument("--landing")
    i.add_argument("--no-push", action="store_true")
    i.add_argument("--sync-after-to-main", action="store_true")
    i.add_argument("--agents")
    i.add_argument("--backplane", action="store_true")
    i.add_argument("--main-branch")
    i.add_argument("--kit-dir")
    i.add_argument("--python")
    i.add_argument("--record-remote")
    i.add_argument("--config")
    i.add_argument("--me")
    i.add_argument("--dry-run", action="store_true")
    u = sub.add_parser("upgrade")
    u.add_argument("dir")
    u.add_argument("--kit-dir")
    u.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    init(a) if a.cmd == "init" else upgrade(a)


if __name__ == "__main__":
    main()
