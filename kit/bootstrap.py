#!/usr/bin/env python3
"""Set a project up with intent-kit, or bring its kit-managed files up to date.

  python bootstrap.py init <dir> --name NAME [--summary TEXT] [choices...] [--dry-run]
  python bootstrap.py upgrade <dir> [--apply]

init works on a new folder (it runs `git init`) or an existing repository (it adopts
it). It only adds: existing files are never overwritten. CLAUDE.md, .gitignore and
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
  --tools-dir PATH                           default tools
  --python CMD                               how the hooks run Python (python3, python, py -3 or a
                                             path); default: the first of those that runs 3.10+
  --record-remote URL                        a private git repo for record/: an empty one gets the
                                             record pushed to it; one holding the record is checked out
  --config answers.json                      the same choices as a JSON object

upgrade compares the project's kit-managed files (the tools, the commit hook and
METHOD.md) with this kit and shows what differs; --apply replaces them, adds any
missing starter files (say, for a layer turned on since), records the kit version
and re-renders METHOD-RULES.md (moving an older inlined rules section out of
CLAUDE.md). Project content is never touched.
"""
import argparse
import difflib
import json
import os
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent
MANAGED = KIT / "template" / "managed"
STARTER = KIT / "template" / "starter"
PHILOSOPHY = KIT / "PHILOSOPHY.md"
VERSION = (KIT / "VERSION").read_text(encoding="utf-8").strip()
CONFIG_NAME = "intent-kit.json"
TOOL_FILES = ["kitlib.py", "capture_session.py", "extract_human_messages.py", "to_main.py",
              "sync.py", "land.py", "kit.py", "record_secrets.py"]
LAYERS = {"research": "research", "concepts": "concepts", "experiments": "experiments"}
STANCES = {"wide-search", "forward-plausibility"}
GITIGNORE = ["/record/", "/.claude/current-session", "/.claude/record-turns/",
             "/.claude/settings.local.json", "__pycache__/"]
# Only for a new project: in an existing one, an ignored out/ could hide real work, and a new
# .gitattributes could renormalize line endings so files look changed. Suggested instead.
NEW_ONLY_GITIGNORE = ["/out/"]
NEW_ONLY_STARTERS = [".gitattributes"]
HOOK_EVENTS = ["SessionStart", "Stop", "SessionEnd"]
HOOK = ".githooks/prepare-commit-msg"
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


def git(*args, cwd, check=False, input=None, env=None):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True,
                       encoding="utf-8", input=input, env=env)
    if check and r.returncode != 0:
        sys.exit(f"bootstrap: FAILED: git {' '.join(args)}:\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def fill(text: str, cfg: dict) -> str:
    return (text.replace("{{PROJECT}}", cfg["project"])
                .replace("{{SUMMARY}}", cfg.get("summary") or "*(One-paragraph summary to come.)*")
                .replace("{{TOOLS}}", cfg["tools_dir"]))


def managed_files(cfg: dict) -> dict[str, Path]:
    """Project path -> kit source, for every file the kit owns."""
    m = {f"{cfg['tools_dir']}/{n}": MANAGED / "tools" / n for n in TOOL_FILES}
    m[".githooks/prepare-commit-msg"] = MANAGED / ".githooks" / "prepare-commit-msg"
    m["METHOD.md"] = PHILOSOPHY
    return m


def starter_files(cfg: dict) -> dict[str, str]:
    """Project path -> text, for files the kit creates once and the project then owns."""
    s = {}
    for rel in ["intent/README.md", "intent/vision.md", "plan/requirements.md",
                "plan/decisions/README.md", "plan/lessons/README.md"]:
        s[rel] = fill((STARTER / rel).read_text(encoding="utf-8"), cfg)
    for layer in cfg["layers"]:
        s[f"{LAYERS[layer]}/README.md"] = fill(
            (STARTER / "layers" / layer / "README.md").read_text(encoding="utf-8"), cfg)
    return s


def readme_text(cfg: dict) -> str:
    t = cfg["tools_dir"]
    rows = ["intent/log/       the owner's words, verbatim, append-only (I-xxxx)",
            "intent/vision.md  current view, synthesized from the log",
            "plan/             requirements (R-), decisions (D-), lessons learned (L-)"]
    if "research" in cfg["layers"]:
        rows.append("research/         what is known outside this project, with sources (N-)")
    if "concepts" in cfg["layers"]:
        rows.append("concepts/         candidate designs and hypotheses (C-)")
    if "experiments" in cfg["layers"]:
        rows.append("experiments/      builds, tests and calculations that answer open questions (E-)")
    rows.append(f"{t + '/':<18}record-keeping scripts (intent-kit)")
    head = "**Confidential. Never publish this repository.**\n\n" if cfg["visibility"] == "confidential" else ""
    return (f"# {cfg['project']}\n\n{head}{cfg.get('summary') or ''}\n\n"
            "## How this repo works\n\n```\n" + "\n".join(rows) + "\n```\n\n"
            "The human's intent is recorded verbatim, projected into a current vision and plan, and "
            "corrected by what the work teaches. Raw AI session transcripts live in a separate private "
            "repository (`record/`, gitignored); commits here reference them by a `Session:` trailer. "
            "See [METHOD.md](METHOD.md).\n")


def claude_text(cfg: dict) -> str:
    return (f"# {cfg['project']} — working rules for agents\n\n"
            f"{cfg.get('summary') or ''}\n\n"
            "## Project rules\n\n*(Project-specific working rules go here.)*\n")


def merged_settings(path: Path, cfg: dict) -> str | None:
    """New settings.json text with the capture hooks added, or None if nothing to add."""
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    cmd = f'{cfg["python"]} "$CLAUDE_PROJECT_DIR/{cfg["tools_dir"]}/capture_session.py"'
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
        "agents": a.agents, "main_branch": a.main_branch, "tools_dir": a.tools_dir,
        "layers": [x for x in a.layers.split(",") if x] if a.layers is not None else None,
        "stances": [x for x in a.stances.split(",") if x] if a.stances is not None else None,
        "push_on_land": False if a.no_push else None, "backplane": True if a.backplane else None,
        "sync_after_to_main": True if a.sync_after_to_main else None,
        "python": a.python,
    }
    cfg.update({k: v for k, v in given.items() if v is not None})
    defaults = {"summary": "", "visibility": "confidential", "layers": [], "stances": [],
                "landing": "linear", "push_on_land": True, "sync_after_to_main": False, "agents": "claude-only",
                "backplane": False,
                "tools_dir": "tools", "record_commit_every": 10, "not_human_prefixes": [], "sources": {}}
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
    r = subprocess.run([sys.executable, str(root / cfg["tools_dir"] / "kit.py"), *args],
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
    config = {"kit_version": VERSION, **{k: cfg[k] for k in (
        "project", "summary", "main_branch", "tools_dir", "python", "visibility", "layers", "stances", "landing",
        "push_on_land", "sync_after_to_main", "agents", "backplane", "record_commit_every", "not_human_prefixes",
        "sources")}}

    # --- what's in the way? nothing is written until this is empty ---
    blockers = []
    if (root / "METHOD-RULES.md").exists():
        blockers.append("METHOD-RULES.md exists; the kit generates that file")
    if (root / CONFIG_NAME).exists():
        blockers.append(f"{CONFIG_NAME} exists: this project is already set up (use `upgrade`)")
    for rel, src in managed_files(cfg).items():
        p = root / rel
        if p.exists() and p.read_bytes() != src.read_bytes():
            blockers.append(f"{rel} exists and isn't the kit's (choose another --tools-dir, or move it)")
    if is_repo:
        if git("ls-files", "--", "record", cwd=root).stdout.strip():
            blockers.append("record/ is tracked by this repository; the record must be a separate repo")
        hp = git("config", "core.hooksPath", cwd=root).stdout.strip()
        if hp and hp != ".githooks":
            blockers.append(f"core.hooksPath is already {hp!r}; the Session: trailer hook needs .githooks")
        own = root / ".git" / "hooks" / "prepare-commit-msg"
        if own.is_file() and not hp:
            blockers.append(".git/hooks/prepare-commit-msg exists and would stop running; merge it into "
                            ".githooks/ by hand first")
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
    suggestions = []
    for rel in NEW_ONLY_STARTERS:
        if (root / rel).exists():
            continue
        if is_repo:
            suggestions.append(f"{rel}: none here. The kit's ({(STARTER / rel).read_text(encoding='utf-8').splitlines()[0]}, ...) "
                               "keeps line endings consistent, but adding it to an existing repo can make files "
                               "look changed. Check `git ls-files --eol` first.")
        else:
            writes[rel] = (STARTER / rel).read_text(encoding="utf-8")
    if not (root / "README.md").exists():
        writes["README.md"] = readme_text(cfg)
    if not (root / "CLAUDE.md").exists():
        writes["CLAUDE.md"] = claude_text(cfg)
    writes[CONFIG_NAME] = json.dumps(config, indent=2) + "\n"
    if new_settings:
        writes[".claude/settings.json"] = new_settings
    gi = root / ".gitignore"
    have = gi.read_text(encoding="utf-8").splitlines() if gi.is_file() else []
    wanted = GITIGNORE + ([] if is_repo else NEW_ONLY_GITIGNORE)
    missing = [ln for ln in wanted if ln not in have]
    if is_repo and "/out/" not in have:
        suggestions.append("out/: not ignored here. Write to_main.py drafts in a temp or scratch folder, or "
                           "ignore a drafts folder of your choosing.")
    if missing:
        base = gi.read_text(encoding="utf-8") if gi.is_file() else ""
        sep = "" if not base else ("\n" if base.endswith("\n") else "\n\n")
        writes[".gitignore"] = base + sep + "# intent-kit: the private record is its own repo; local state\n" \
            + "\n".join(missing) + "\n"

    print(f"bootstrap: {'adopting' if is_repo else 'creating'} {root} (kit {VERSION})")
    for rel in sorted(writes):
        verb = "update" if (root / rel).exists() else "add"
        print(f"  {verb:6} {rel}")
    for rel in skipped:
        print(f"  keep   {rel} (exists; left as it is)")
    print(f"  record/ as its own git repo{' (exists)' if (root / 'record' / '.git').exists() else ''}"
          + (f", remote {remote}" if remote else ", local only (no remote)"))
    print(f"  hooks run Python as: {cfg['python']}")
    print("  git config core.hooksPath .githooks")
    print("  render METHOD-RULES.md and import it from CLAUDE.md (one @METHOD-RULES.md line)")
    for s_ in suggestions:
        print(f"  suggest (not done) {s_}")
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
        if rel.startswith(".githooks/"):
            p.chmod(0o755)
    git("config", "core.hooksPath", ".githooks", cwd=root, check=True)
    if run_tool(root, cfg, "record", *(["--remote", remote] if remote else [])) != 0:
        print("bootstrap: the record isn't fully set up (see above); fix it, then run "
              f"python {cfg['tools_dir']}/kit.py record" + (f" --remote {remote}" if remote else ""))
    run_tool(root, cfg, "render")
    # Windows doesn't record the executable bit, and macOS and Linux skip a hook without it,
    # so git's copy is marked executable whatever this machine is.
    if is_repo:
        git("add", "--chmod=+x", "--", HOOK, cwd=root, check=True)
        print(f"bootstrap: staged {HOOK} as executable (git skips a hook that isn't, on macOS and Linux)")
    else:
        git("add", "-A", cwd=root, check=True)
        git("update-index", "--chmod=+x", "--", HOOK, cwd=root, check=True)
        git("commit", "-q", "-m", f"Set up {cfg['project']} with intent-kit {VERSION}", cwd=root, check=True)
        print(f"bootstrap: committed the scaffold on {cfg['main_branch']}")
    run_tool(root, cfg, "check")
    t = cfg["tools_dir"]
    print("\nbootstrap: next steps (ONBOARDING.md has the detail):")
    if is_repo:
        print(f"  - review and commit the scaffold on {cfg['main_branch']} (git status)")
        print(f"  - sweep this project's earlier sessions into the record: python {t}/capture_session.py --all --commit")
    print(f"  - cite the owner's onboarding answers in {CONFIG_NAME} (not as intent): "
          f"python {t}/kit.py cite <session-id> --msg <n> --keys <settings>")
    print(f"  - capture the owner's first words about the project as I-0001: "
          f"python {t}/extract_human_messages.py <session-id> --list")
    print(f"  - write intent/vision.md from them, then python {t}/to_main.py docs -m \"...\"")


def upgrade(a):
    root = Path(a.dir).resolve()
    cfg_path = root / CONFIG_NAME
    if not cfg_path.is_file():
        sys.exit(f"bootstrap: {root} has no {CONFIG_NAME}; use `init`")
    cfg = {"tools_dir": "tools", "layers": [], "project": root.name, "summary": "",
           **json.loads(cfg_path.read_text(encoding="utf-8"))}
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
    mode = git("ls-files", "-s", "--", HOOK, cwd=root).stdout.split()
    hook_not_x = bool(mode) and mode[0] != "100755"
    if hook_not_x:
        print(f"--- {HOOK}: tracked as not executable, so git on macOS and Linux skips it; the kit would fix that")
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
        git("update-index", "--chmod=+x", "--", HOOK, cwd=root, check=True)
        print(f"bootstrap: staged {HOOK} as executable; commit it")
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    data["kit_version"] = VERSION
    for k, v in ADDED_SETTINGS.items():  # settings added in later kit versions, at their defaults
        data.setdefault(k, v)
    cfg_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    run_tool(root, cfg, "render")
    print(f"bootstrap: updated {len(changed) + len(new_starters)} file(s) to kit {VERSION}. Commit the tools "
          f"as usual; publish {CONFIG_NAME}, METHOD-RULES.md and CLAUDE.md with tools/to_main.py docs.")
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
    i.add_argument("--tools-dir")
    i.add_argument("--python")
    i.add_argument("--record-remote")
    i.add_argument("--config")
    i.add_argument("--dry-run", action="store_true")
    u = sub.add_parser("upgrade")
    u.add_argument("dir")
    u.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    init(a) if a.cmd == "init" else upgrade(a)


if __name__ == "__main__":
    main()
