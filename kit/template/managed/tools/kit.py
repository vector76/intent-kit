#!/usr/bin/env python3
"""Keep this project's intent-kit setup honest.

  python intent-kit/tools/kit.py render    regenerate METHOD-RULES.md from intent-kit/config.json, and make
                                sure CLAUDE.md imports it
  python intent-kit/tools/kit.py check     verify the setup; exit 1 if anything is wrong
  python intent-kit/tools/kit.py cite <session-id> --msg N [N ...] --keys visibility,layers
                                record which of the owner's messages set those choices
  python intent-kit/tools/kit.py record [--remote URL]
                                set record/ up as its own git repo (on a fresh clone too), and
                                connect it to a private remote: an empty one gets the record
                                pushed to it, one that already holds the record is checked out
  python intent-kit/tools/kit.py whoami [--set NAME]
                                show (or set) the name this clone records sessions and intent under
  python intent-kit/tools/kit.py attribute NAME [--apply]
                                name NAME as the author of every intent entry on main that names
                                none; only when NAME says those words are all theirs

METHOD-RULES.md is generated (intent-kit/METHOD-RULES.md): to change how the project is run, change intent-kit/config.json
(citing what asked for it under "sources"), re-render, and publish both with
`intent-kit/tools/to_main.py docs`. CLAUDE.md stays the project's own; it holds one
`@intent-kit/METHOD-RULES.md` line, which Claude Code reads as an import.

The owner's onboarding answers are cited from the config (`cite`), not captured as
intent entries: setting the project up isn't intent about the project. Changes the
owner asks for later are captured as intent like anything else, and cited by entry id.

Managed by intent-kit.
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import (CONFIG_NAME, DEFAULTS, KIT_DIR, MAIN, MIN_PYTHON, RECORD, REPO, TARGET, TOOLS_REL,  # noqa: E402
                    checkout_of, git, kp,
                    kinds, load_config, main_file_text, main_tree_files, my_name, python_version,
                    record_problem, set_my_name, suggested_name, with_trailer, yaml_str)

RULES_NAME = kp("METHOD-RULES.md")  # repo-relative
HOOK = kp("githooks/prepare-commit-msg")
HOOKS_PATH = kp("githooks")
IMPORT = "@" + RULES_NAME
BEGIN = "<!-- intent-kit:begin -->"  # an older kit inlined the rules in CLAUDE.md between these
END = "<!-- intent-kit:end -->"
MANAGED = ["kitlib.py", "capture_session.py", "extract_human_messages.py", "to_main.py",
           "sync.py", "land.py", "kit.py", "record_secrets.py"]
CLAUDE_POINTER = (
    "## How this project keeps its record\n\n"
    f"This project follows the intent-kit method. Everything the kit adds is in `{KIT_DIR}/`: "
    f"`{KIT_DIR}/METHOD.md` explains the method, and the working rules below are generated into "
    f"`{RULES_NAME}` from `{CONFIG_NAME}`. Project-specific rules belong in this file, not that one."
    "\n\n" + IMPORT + "\n")


def render_rules(cfg: dict) -> str:
    t = TOOLS_REL
    py = cfg.get("python") or "python"
    layers = cfg.get("layers", [])
    stances = cfg.get("stances", [])
    k = kinds(cfg)
    rows = [
        ("Intent (people's own words, verbatim, each naming its author)", "`§/intent/log/`", "I-0001",
         "append-only, never edit"),
        ("Vision (current view)", "`§/intent/vision.md`", "—", "rewritten to stay current"),
        ("Requirements", "`§/plan/requirements.md`", "R-001", "current view only"),
        ("Decisions", "`§/plan/decisions/`", "D-0001", "a decision can be replaced by a new one"),
        ("Lessons (postmortems)", "`§/plan/lessons/`", "L-0001", "append-only"),
    ]
    if "research" in layers:
        rows.append(("Research (what's known outside this project)", "`§/research/`", "N-0001",
                     "a note can be corrected; cite sources"))
    if "concepts" in layers:
        rows.append(("Concepts (candidate designs, hypotheses)", "`§/concepts/`", "C-0001",
                     "revised in place; set aside, not deleted"))
    if "experiments" in layers:
        rows.append(("Experiments (builds, tests, calculations, models)", "`§/experiments/`", "E-0001",
                     "the record of a question and its answer"))
    rows.append(("Raw sessions, candid notes", "`§/record/` (separate private git repo)", "session id",
                 "append-only"))
    table = "| Layer | Where | IDs | Mutability |\n|---|---|---|---|\n" + "\n".join(
        f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)

    sources = "I-" + "".join(f"/{p}-" for p in (["E"] if "experiments" in layers else [])
                             + (["N"] if "research" in layers else []))
    cite = (f"Cite IDs wherever something is derived: requirements cite {sources} entries, "
            f"decisions cite {sources}/R-")
    cite += ", and experiments cite the question they answer." if "experiments" in layers else "."

    rules = [
        "**Intent is people's own words, verbatim and append-only.** Never edit or paraphrase "
        f"`§/intent/log/`. Capture new intent with `{py} {t}/extract_human_messages.py <session-id> "
        "--slug <name> --msg <n> [...]` (see `§/intent/README.md`); it commits the entry to main at once. "
        "Intent about how the project is run and recorded is intent too, and goes in the same log. "
        "When someone states, refines or changes intent, capture it before the session ends, then "
        "update `§/intent/vision.md` (and `§/plan/requirements.md` if affected). "
        "When a message answers your questions and can't be understood without them (\"1: yes, 2: no\"), "
        "add `--question \"<the question, quoted exactly>\"` for each question it depends on; the tool checks "
        "they're your words from that session and marks them as not intent. That's a judgment call, not a rule: "
        "if the words make sense on their own, add no question, and never add more than the words need. "
        "**Before ending a session, "
        "run `--list` again: every message not marked `*` that states, refines or changes intent needs "
        "an entry.** Count; don't trust the filter.",
        "**Current-view documents carry no history.** `§/intent/vision.md` and `§/plan/requirements.md` say "
        "only what is true now: no \"superseded\" or \"previously\" sections, no changelogs, no "
        "strike-throughs. Git is the history. Keep a short reason only where a point would otherwise "
        "look wrong (\"because E-0004 showed ...\").",
        "**Every entry says according to whom.** An intent entry's `author:` is the person who typed "
        "the words. A session is one person's (it can't be shared or handed over), and the extractor "
        "takes the author from it. Never record words as anyone else's. When someone relays another "
        "person's wishes (\"Alice wants X\"), capture it with `--on-behalf-of Alice`: it stays the "
        "speaker's entry, and it counts as the speaker's view of what that person wants, not as their "
        "intent, until they say it themselves. Agreeing is a new entry by the person who agrees. A "
        "decision says who agreed to it (`agreed_by:`), and a lesson who found the problem (`found_by:`). "
        "This isn't proof of identity; it's so people know whom to talk to.",
        "**Surface contradictions; don't resolve them silently.** If intent entries conflict, or a "
        "request conflicts with the vision, list it under *Open questions and tensions* in "
        "`§/intent/vision.md` and ask. Don't pick a side on your own. The vision and requirements are "
        "written as the consensus and name no one. Where people's intent differs, the open question "
        "names who holds each view, so they can talk it through; never decide between people.",
    ]
    if "wide-search" in stances:
        rules.append(
            "**Don't narrow the search early.** An example in the intent is an example. Don't turn one "
            "into a requirement or a decision without the owner saying so, and when presenting options, "
            "show the spread rather than converging on a favorite.")
    if "research" in layers:
        rules.append(
            "**Keep what's known apart from what's wanted.** Facts about the world go in `§/research/` with "
            "sources a reader can check. Mark anything unverified as such. Never invent citations. Intent "
            "is the owner's; research is the world's; don't blend them.")
    if "forward-plausibility" in stances:
        rules.append(
            "**Judge plausibility looking forward, not by consensus.** When a path was tried and "
            "abandoned, record *what blocked it* and whether that still holds with current tools. Name the "
            "enabling milestones that would open the path. \"Nobody has done it\" and \"it failed before\" "
            "are facts to note, not verdicts.")
    if "experiments" in layers:
        rules.append(
            "**Experiments close the loop.** Each experiment states its question (tied to a tension or "
            "requirement), what was done, the result, and what it changed. If it changed the intent, the "
            "owner confirms that and it becomes a new intent entry.")
    rules.append(
        "**Read `§/plan/lessons/` before related work.** When a mistake is found, write an L- entry: what "
        "happened, which session and commit, root cause, how to avoid it. If the fix is a rule, add it to "
        f"CLAUDE.md ({RULES_NAME} is generated and would lose it).")
    if cfg.get("visibility") == "publishable":
        rules.append(
            "**Publishable.** This repository is meant to be shareable. Keep personal details, account "
            "information, credentials and absolute paths under a home directory out of it. Anything too "
            "candid goes in the private record (`§/record/notes/`), with a neutral one-line pointer here.")
    else:
        rules.append(
            "**Confidential.** This repository is never published: no public remote, no sharing. When "
            "searching the web or using outside services, ask generic questions about the subject, and "
            "never describe the project's concept, design or goals in a query or request.")
    rules.append(
        "**The record is private and separate.** `§/record/` is its own git repository, ignored by this "
        "one. It holds raw transcripts (system prompts, file contents, personal details). Never copy its "
        "raw content into this repo, never add it to this repo, and never push it anywhere the owner "
        "hasn't set up. It may have its own private remote.")
    numbered = "\n".join(f"{i}. {r}" for i, r in enumerate(rules, 1))

    entry_kinds = [n for n in k if n != "intent"]
    names = {"decision": "decisions", "lesson": "lessons", "research": "research notes",
             "concept": "concepts", "experiment": "experiments"}
    kind_list = ", ".join(names[n] for n in entry_kinds)
    land = ("rebases it onto main and fast-forwards main, never a merge commit"
            if cfg.get("landing", "linear") == "linear" else "merges it into main with a merge commit")
    push = " Then it pushes main to every remote." if cfg.get("push_on_land", True) else ""
    branches = [
        "**Numbered entries go straight to main when they are created**, whatever branch or worktree "
        f"you are in. `extract_human_messages.py` does this for intent; `{py} {t}/to_main.py <kind> "
        f"--slug <name> --file <draft.md>` does it for {kind_list} (kinds: {', '.join(entry_kinds)}). "
        "Write the draft outside tracked files (a temp or scratch folder) with `{ID}` where the number "
        "goes. The "
        "tool takes the next free number from main under a lock shared by every worktree and commits only "
        "that file. Never number an entry by hand. "
        + ("Your branch is then synced with main." if cfg.get("sync_after_to_main") else
           "Your branch doesn't get the entry until it next syncs, and doesn't need it: numbers come "
           "from main.")
        + (" For an experiment this creates its folder's README on main; the work then continues on your "
           "branch" + ("." if cfg.get("sync_after_to_main") else
                       f" once you've synced it (`{py} {t}/sync.py`).")
           if "experiments" in layers else ""),
        "**Current-view documents go to main right after you edit them:** `§/intent/vision.md`, everything "
        f"under `§/plan/`, `CLAUDE.md`, `{CONFIG_NAME}` and `{RULES_NAME}`. Run `{py} {t}/to_main.py docs -m \"<what "
        "changed>\"`. If main's copy changed in a conflicting way, nothing is copied and the conflict is "
        "reported. That usually means two threads disagree: tell the owner rather than resolving it.",
        f"**Everything else waits for landing:** `{py} {t}/land.py [branch]` {land}.{push} Land when "
        "the owner asks. Intent captured in a worktree that never lands is still on main; that's intended.",
        f"At the start of a session in a worktree or on a branch other than main, run `{py} {t}/sync.py` "
        "to bring it up to date. On a conflict it changes nothing; tell the owner.",
        "Before relying on a worktree's isolation, check `git worktree list`. In a checkout another agent "
        "may also be using, commit only your own paths (`git commit -- <paths>`), never `git commit -a` "
        "or `git add -A`.",
    ]
    branch_text = "\n".join(f"- {b}" for b in branches)

    capture = (
        f"Hooks in `.claude/settings.json` run `{t}/capture_session.py`. It copies each session's "
        "transcript into `§/record/sessions/` (worktree sessions included) and commits the record repo at "
        f"session start, every {cfg.get('record_commit_every', 10)} turns and at session end. Sweep by "
        f"hand with `{py} {t}/capture_session.py --all --commit`. Commits here get a `Session: <id>` "
        "trailer from `§/githooks/prepare-commit-msg` (enabled by `git config core.hooksPath §/githooks`), "
        "linking each commit to the session that made it; don't remove it. "
        "If the session start says this clone doesn't know who is working in it, ask the person what to "
        f"call them before other work, suggest the name it offers, and run `{py} {t}/kit.py whoami --set "
        "\"<name>\"` with the name they give. "
        f"`{py} {t}/kit.py check` verifies the whole setup. If the session start says the session is NOT "
        "being recorded, tell the owner. On a fresh clone the fix is usually `git config core.hooksPath "
        f"§/githooks` and `{py} {t}/kit.py record --remote <the record's private url>`."
        "\n\n**Secrets in the record.** Transcripts keep whatever passed through a session, keys and "
        "passwords included. The hooks scan new text for likely secrets. If the session start says the "
        "record holds some, tell the owner, show them the masked list "
        f"(`{py} {t}/record_secrets.py`), and suggest revoking any real one. Scrubbing rewrites the "
        f"record's history (`{py} {t}/record_secrets.py scrub <id>`), so do it only when the owner asks. "
        "Never print, repeat or search for a secret's full text: it would land in this session's "
        "transcript too.")
    if cfg.get("agents", "claude-only") == "claude-only":
        capture += ("\n\nUse Claude as the agent here: other agents leave no Claude transcript, so their "
                    "sessions would be missing from the record.")
    else:
        capture += ("\n\nOther agents may be used, but only Claude sessions are captured automatically. "
                    "For another agent's session, save what you can of it under `§/record/notes/`, and "
                    f"capture the owner's intent from it verbatim with `{t}/to_main.py intent`.")
    capture += ("\n\nWhen extracting intent from a forked or resumed session, the handed-over context at "
                "the start shows up as messages but is already captured (marked `*`) or isn't the owner's "
                "words: skip it.")

    parts = [
        "# How this project keeps its record",
        "",
        f"<!-- Generated from {CONFIG_NAME} by {t}/kit.py render, and imported by CLAUDE.md. Change the "
        "config and re-render; edits made here are overwritten. -->",
        "",
        "Intent is recorded verbatim, projected into a current vision and plan, and corrected by what "
        "the work teaches; every output traces back to the session that made it and the intent in force "
        "at the time. `§/METHOD.md` explains why. Read `§/intent/vision.md` before any work.",
        "",
        "## Layers and IDs",
        "",
        table,
        "",
        cite,
        "",
        "## Rules",
        "",
        numbered,
        "",
        "## Branches and worktrees",
        "",
        "Work may happen in git worktrees (Claude Code's, Backplane's or your own) or on branches. The "
        "record stays consistent like this:",
        "",
        branch_text,
        "",
        "## Session capture",
        "",
        capture,
    ]
    if cfg.get("backplane"):
        parts += [
            "",
            "## Backplane",
            "",
            "- Threads run in worktrees under `.backplane/worktrees/`; their sessions are captured like any "
            "other, into the one `§/record/`.",
            "- Don't name a remote `origin`: Backplane branches new threads from origin's default branch, "
            "skipping local main.",
            "- Subthreads, and threads an agent launches, may run in the main checkout instead of a worktree. "
            "Check `git worktree list` before relying on isolation.",
            "- Thread reports (`[Backplane] ...`) are not the owner's words; the extractor skips them. "
            "Messages other threads send carry no marker: read before capturing.",
            "- Backplane doesn't see local landings: settle the thread there afterwards.",
        ]
    parts += ["", "## Numbering", "",
              "IDs are sequential within their folder and are assigned by the tools above, from main. "
              "Requirements (R-) are numbered by hand in `§/plan/requirements.md`, which is a current-view "
              "document, and keep their number when others are added or removed.",
              "", "## Where the project's setup came from", "",
              f"The choices in `{CONFIG_NAME}` cite what set them under `\"sources\"`. The owner's answers "
              "at onboarding are cited by session and message (the words are in the record), not captured "
              "as intent: setting the project up isn't intent about the project. A change the owner asks "
              "for later is captured as intent like anything else, then cited by its I- id: "
              f"`{py} {t}/kit.py cite <session-id> --msg <n> --keys <setting>` or edit the config by hand."]
    return ("\n".join(parts) + "\n").replace("§/", KIT_DIR + "/")


def with_import(text: str) -> str:
    """CLAUDE.md text that imports the rules, replacing an older inlined section if present."""
    if BEGIN in text and END in text:
        pre, rest = text.split(BEGIN, 1)
        post = rest.split(END, 1)[1]
        rest = post.lstrip("\n")
        return pre.rstrip() + "\n\n" + CLAUDE_POINTER + ("\n" + rest if rest.strip() else "")
    if any(line.strip() == IMPORT for line in text.splitlines()):
        return text
    return text.rstrip() + "\n\n" + CLAUDE_POINTER


HOOK_EVENTS = ("SessionStart", "Stop", "SessionEnd")
SESSION_END_TIMEOUT = 30  # seconds; Claude Code gives SessionEnd hooks 1.5 s unless told otherwise


def hook_command(cfg: dict) -> str:
    py = cfg.get("python") or "python"
    if " " in py and Path(py).is_file():
        py = f'"{py}"'
    return f'{py} "$CLAUDE_PROJECT_DIR/{TOOLS_REL}/capture_session.py"'


def capture_hooks(settings: dict):
    """Every capture_session.py hook entry in a settings.json object, by event."""
    for event in HOOK_EVENTS:
        for grp in settings.get("hooks", {}).get(event, []):
            for h in grp.get("hooks", []):
                if "capture_session.py" in h.get("command", ""):
                    yield event, h


def render(root: Path = REPO) -> bool:
    cfg = load_config(root)
    changed = False
    rules = root / RULES_NAME
    new_rules = render_rules(cfg)
    if not rules.is_file() or rules.read_text(encoding="utf-8") != new_rules:
        rules.write_text(new_rules, encoding="utf-8", newline="\n")
        print(f"kit: {RULES_NAME} rendered")
        changed = True
    path = root / "CLAUDE.md"
    old = path.read_text(encoding="utf-8") if path.is_file() else f"# {cfg.get('project') or 'Project'}\n"
    new = with_import(old)
    if new != old:
        path.write_text(new, encoding="utf-8", newline="\n")
        print(f"kit: CLAUDE.md now imports {RULES_NAME}")
        changed = True
    sp = root / ".claude" / "settings.json"
    try:
        settings = json.loads(sp.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        settings = None
    if settings is not None:
        want, fixed = hook_command(cfg), 0
        for event, h in capture_hooks(settings):
            if h.get("command") != want:
                h["command"], fixed = want, fixed + 1
            if event == "SessionEnd" and h.get("timeout", 0) < SESSION_END_TIMEOUT:
                h["timeout"], fixed = SESSION_END_TIMEOUT, fixed + 1
        if fixed:
            sp.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8", newline="\n")
            print(f"kit: .claude/settings.json hooks now run {want}, with {SESSION_END_TIMEOUT}s to commit at "
                  "session end")
    print(f"kit: publish with {TOOLS_REL}/to_main.py docs" if changed else "kit: rules already current")
    return changed


def cite(session: str, msgs: list[int], keys: list[str], root: Path = REPO):
    """Record, under "sources", the owner's messages that set these config keys."""
    from extract_human_messages import human_messages, resolve
    found = human_messages(resolve(session))
    if any(n < 1 or n > len(found) for n in msgs):
        sys.exit(f"kit: --msg numbers run from 1 to {len(found)}; see extract_human_messages.py --list")
    unknown = [k for k in keys if k not in DEFAULTS or k in ("sources", "kit_version")]
    if unknown:
        sys.exit(f"kit: not config settings: {', '.join(unknown)}")
    path = root / CONFIG_NAME
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = data.setdefault("sources", {})
    refs = [{"session": found[n - 1][1], "message": found[n - 1][0]} for n in msgs]
    for k in keys:
        have = sources.setdefault(k, [])
        have += [r for r in refs if r not in have]
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"kit: cited {len(refs)} message(s) for {', '.join(keys)} in {CONFIG_NAME} "
          f"(publish with {TOOLS_REL}/to_main.py docs)")


RECORD_README = """# Record (private)

The raw session transcripts of {project}, copied here by the project's
`capture_session.py` hooks, and candid notes (`notes/`). This is its own git repository,
deliberately kept out of the project repository: transcripts hold system prompts, file
contents, tool output and personal details.

Never publish it. It may have a private remote of its own, for backup or so that
several people can push and pull the record. Session files are named by their unique
session id, so merging records from several machines doesn't conflict.
"""


def setup_record(remote: str | None = None) -> int:
    """Make record/ its own git repo if it isn't, and connect it to a private remote."""
    p = record_problem(need_repo=False)
    if p:
        sys.exit(f"kit: FAILED: {p}; record/ was left as it is")
    quiet = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}  # fail rather than wait for a password
    RECORD.mkdir(parents=True, exist_ok=True)
    if not (RECORD / ".git").exists():
        git("init", "-q", "-b", "main", cwd=RECORD, check=True)
        print("kit: record/ is now its own git repository")
    remote_branch = None
    if remote:
        have = git("remote", "get-url", "origin", cwd=RECORD)
        if have.returncode == 0 and have.stdout.strip() != remote:
            sys.exit(f"kit: FAILED: record/ already has a remote 'origin' ({have.stdout.strip()}); "
                     "change it with git -C record remote set-url origin <url>")
        if have.returncode != 0:
            git("remote", "add", "origin", remote, cwd=RECORD, check=True)
        f = git("fetch", "-q", "origin", cwd=RECORD, env=quiet)
        if f.returncode != 0:
            sys.exit(f"kit: FAILED: can't fetch the record's remote {remote}:\n{f.stderr.strip()}")
        heads = git("for-each-ref", "--format=%(refname:lstrip=3)", "refs/remotes/origin", cwd=RECORD).stdout.split()
        heads = [h for h in heads if h != "HEAD"]
        remote_branch = "main" if "main" in heads else (heads[0] if heads else None)
    has_commits = git("rev-parse", "-q", "--verify", "HEAD", cwd=RECORD).returncode == 0
    if remote_branch and not has_commits:
        r = git("checkout", "-q", "-B", remote_branch, "--track", f"origin/{remote_branch}", cwd=RECORD)
        if r.returncode != 0:
            sys.exit(f"kit: FAILED: can't check out the record from {remote}:\n{r.stderr.strip()}\n"
                     "Files already in record/ are in the way; move them aside and run this again.")
        print(f"kit: record/ checked out from {remote}")
        has_commits = True
    elif remote_branch and git("merge-base", "HEAD", f"origin/{remote_branch}", cwd=RECORD).returncode != 0:
        print(f"kit: record/ and {remote} both hold a record, with unrelated histories. Nothing was merged; "
              f"to combine them: git -C record pull --allow-unrelated-histories origin {remote_branch}")
    (RECORD / "sessions").mkdir(exist_ok=True)
    (RECORD / "notes").mkdir(exist_ok=True)
    readme = RECORD / "README.md"
    if not readme.exists():
        project = load_config().get("project") or MAIN.name
        readme.write_text(RECORD_README.format(project=project), encoding="utf-8", newline="\n")
    git("add", "-A", cwd=RECORD)
    if git("diff", "--cached", "--quiet", cwd=RECORD).returncode != 0:
        git("commit", "-q", "-m", "Set up the record" if has_commits else "Start the private record",
            cwd=RECORD, check=True)
    if remote and not remote_branch:  # an empty remote: give it the record and track it
        branch = git("symbolic-ref", "--short", "HEAD", cwd=RECORD).stdout.strip() or "main"
        r = git("push", "-q", "-u", "origin", branch, cwd=RECORD, env=quiet)
        if r.returncode != 0:
            print(f"kit: PROBLEM: couldn't push the record to {remote}:\n{r.stderr.strip()}")
            return 1
        print(f"kit: record/ pushed to {remote} and tracks it")
    elif remote:
        print("kit: record/ tracks its remote; push and pull it like any repo (git -C record push)")
    return 0


def whoami(name: str | None) -> int:
    if name is not None:
        if not name.strip() or "\n" in name:
            sys.exit("kit: a name is one line of text")
        set_my_name(name)
        print(f"kit: sessions and intent in this clone are now recorded as {name.strip()}'s "
              "(kept in its git config; not committed)")
        return 0
    have = my_name()
    if have:
        print(f"kit: this clone records sessions and intent as {have}'s")
        return 0
    guess = suggested_name()
    print("kit: this clone doesn't know who works in it. Ask them what to call them"
          + (f" (suggest {guess!r})" if guess else "") + f', then: python {TOOLS_REL}/kit.py whoami --set "<name>"')
    return 1


LOG = kp("intent/log")


def unattributed_entries() -> list[str]:
    """Intent entries on main whose front matter names no author."""
    out = []
    for rel in main_tree_files(LOG):
        if not rel.endswith(".md"):
            continue
        m = re.match(r"---\n(.*?)\n---\n", main_file_text(rel), re.S)
        if m and not re.search(r"(?m)^author:\s*\S", m.group(1)):
            out.append(rel)
    return out


def attribute(name: str, apply: bool) -> int:
    """Add `author: NAME` to the front matter of every intent entry on main that names no author.
    It changes no one's words, but it does touch the append-only log, so it's for one case: the
    entries predate authorship and NAME says they're all theirs."""
    name = name.strip()
    if not name or "\n" in name:
        sys.exit("kit: a name is one line of text")
    todo = unattributed_entries()
    if not todo:
        print("kit: every intent entry on main names its author")
        return 0
    wt = checkout_of(TARGET)
    print(f"kit: {len(todo)} intent entr{'y' if len(todo) == 1 else 'ies'} on {TARGET} name no author:")
    for rel in todo:
        print(f"  {rel}")
    if not apply:
        print(f"kit: run again with --apply to name {name} as the author of all of them. Do that only if "
              f"{name} says those words are all theirs.")
        return 0
    if not wt:
        sys.exit(f"kit: FAILED: check {TARGET} out somewhere first; nothing was changed")
    dirty = git("status", "--porcelain", "--", *todo, cwd=wt).stdout.strip()
    if dirty:
        sys.exit(f"kit: FAILED: {wt} has uncommitted changes to these entries; nothing was changed")
    line = f"author: {yaml_str(name)}"
    for rel in todo:
        path = wt / rel
        text = path.read_text(encoding="utf-8")
        head, rest = text.split("\n---\n", 1)
        lines = head.split("\n")
        at = next((i for i, ln in enumerate(lines) if ln.startswith("captured_from:")),
                  next((i for i, ln in enumerate(lines) if ln.startswith("id:")), 0))
        lines.insert(at + 1, line)
        path.write_text("\n".join(lines) + "\n---\n" + rest, encoding="utf-8", newline="\n")
    git("add", "--", *todo, cwd=wt, check=True)
    msg = with_trailer(f"Attribute {len(todo)} earlier intent entries to {name}\n\n"
                       "Only the author: line was added; the words are unchanged.")
    git("commit", "-q", "-F", "-", "--", *todo, cwd=wt, input=msg, check=True)
    print(f"kit: named {name} as the author of {len(todo)} entr{'y' if len(todo) == 1 else 'ies'}, "
          f"committed on {TARGET}")
    return 0


def check(root: Path = REPO) -> list[str]:
    problems, notes = [], []
    cfg_path = root / CONFIG_NAME
    if not cfg_path.is_file():
        return [f"no {CONFIG_NAME}: this project isn't set up (run the kit's bootstrap.py)"]
    try:
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return [f"{CONFIG_NAME} is not valid JSON: {e}"]
    cfg = load_config(root)
    t = TOOLS_REL

    p = record_problem()
    if p:
        problems.append(p)
    py = cfg.get("python") or "python"
    v = python_version(py)
    if v is None:
        problems.append(f"{py!r}, the Python command in {CONFIG_NAME}, doesn't run here, so the hooks "
                        "record nothing. Set \"python\" to one that does (python3, python, py -3 or a "
                        f"full path) and run python {t}/kit.py render")
    elif v < MIN_PYTHON:
        problems.append(f"{py!r} is Python {v[0]}.{v[1]}; the tools need {MIN_PYTHON[0]}.{MIN_PYTHON[1]} or later")
    if git("config", "core.hooksPath", cwd=root).stdout.strip() != HOOKS_PATH:
        problems.append(f"core.hooksPath is not {HOOKS_PATH}, so commits get no Session: trailer "
                        f"(git config core.hooksPath {HOOKS_PATH})")
    if not (root / HOOK).is_file():
        problems.append(f"{HOOK} is missing")
    mode = git("ls-files", "-s", "--", HOOK, cwd=root).stdout.split()
    if mode and mode[0] != "100755":
        problems.append(f"{HOOK} is tracked as not executable, so git on macOS and Linux "
                        "skips it and commits there get no Session: trailer "
                        f"(git update-index --chmod=+x {HOOK}, then commit)")
    for name in MANAGED:
        if not (root / t / name).is_file():
            problems.append(f"{t}/{name} is missing")
    try:
        hooks = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8")).get("hooks", {})
    except (OSError, json.JSONDecodeError):
        hooks = {}
    found = list(capture_hooks({"hooks": hooks}))
    for event in HOOK_EVENTS:
        if not any(e == event for e, _ in found):
            problems.append(f".claude/settings.json has no {event} hook running capture_session.py")
    if any(h.get("command") != hook_command(cfg) for _, h in found):
        problems.append(f".claude/settings.json hooks don't run {hook_command(cfg)} (python {t}/kit.py render)")
    if any(e == "SessionEnd" and h.get("timeout", 0) < SESSION_END_TIMEOUT for e, h in found):
        problems.append(f"the SessionEnd hook has Claude Code's default 1.5 s, too little to commit the record "
                        f"(python {t}/kit.py render sets {SESSION_END_TIMEOUT} s)")
    claude = root / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8") if claude.is_file() else ""
    if with_import(text) != text:
        problems.append(f"CLAUDE.md doesn't import {RULES_NAME} (python {t}/kit.py render)")
    rules = root / RULES_NAME
    if not rules.is_file():
        problems.append(f"{RULES_NAME} is missing (python {t}/kit.py render)")
    elif rules.read_text(encoding="utf-8") != render_rules(cfg):
        problems.append(f"{RULES_NAME} is stale or was edited by hand (python {t}/kit.py render)")
    if not (root / kp("METHOD.md")).is_file():
        problems.append(f"{kp('METHOD.md')} is missing (the kit's bootstrap.py upgrade restores it)")
    vision = root / kp("intent/vision.md")
    if not vision.is_file():
        problems.append(f"{kp('intent/vision.md')} is missing")
    elif "Open questions and tensions" not in vision.read_text(encoding="utf-8"):
        problems.append(f"{kp('intent/vision.md')} has no 'Open questions and tensions' section")

    # numbered entries on main: no duplicate numbers
    if git("rev-parse", "--verify", "-q", TARGET, cwd=MAIN).returncode == 0:
        for kind, (folder, prefix, _, _) in kinds(cfg).items():
            seen = {}
            for f in main_tree_files(folder):
                top = f[len(folder) + 1:].split("/")[0]
                m = re.match(rf"{prefix}-(\d+)", top)
                if m:
                    seen.setdefault(m.group(1), set()).add(top)
            for num, items in seen.items():
                if len(items) > 1:
                    problems.append(f"{prefix}-{num} is used more than once on {TARGET}: {', '.join(sorted(items))}")
        if not main_tree_files(LOG):
            notes.append("no intent entries on main yet: capture the owner's first words about the project")
    else:
        notes.append(f"no {TARGET} branch yet: make a first commit")
    if not my_name():
        notes.append(f"this clone doesn't know who works in it, so sessions and intent can't be attributed "
                     f"(python {t}/kit.py whoami)")
    if git("rev-parse", "--verify", "-q", TARGET, cwd=MAIN).returncode == 0:
        n_anon = len(unattributed_entries())
        if n_anon:
            notes.append(f"{n_anon} intent entr{'y names' if n_anon == 1 else 'ies name'} no author. If one person "
                         f"said them all and agrees, python {t}/kit.py attribute \"<name>\" names them")
    if not cfg.get("sources"):
        notes.append(f"{CONFIG_NAME} has no \"sources\": cite the owner's messages that set its choices "
                     f"(python {t}/kit.py cite ...)")
    if (RECORD / ".git").is_dir():
        import record_secrets
        n_open = len(record_secrets.open_findings())
        if n_open:
            notes.append(f"the record holds {n_open} possible secret(s) not yet dealt with "
                         f"(python {t}/record_secrets.py; tell the owner)")
    for n in notes:
        print(f"kit: note: {n}")
    return problems


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "render":
        render()
    elif cmd == "cite":
        ap = argparse.ArgumentParser(prog="kit.py cite")
        ap.add_argument("session")
        ap.add_argument("--msg", type=int, nargs="+", required=True, help="message numbers from --list")
        ap.add_argument("--keys", required=True, help="comma-separated config settings")
        a = ap.parse_args(sys.argv[2:])
        cite(a.session, a.msg, [k.strip() for k in a.keys.split(",") if k.strip()])
    elif cmd == "record":
        ap = argparse.ArgumentParser(prog="kit.py record")
        ap.add_argument("--remote", help="URL of a private git repository for the record")
        sys.exit(setup_record(ap.parse_args(sys.argv[2:]).remote))
    elif cmd == "whoami":
        ap = argparse.ArgumentParser(prog="kit.py whoami")
        ap.add_argument("--set", dest="name", metavar="NAME", help="what to call the person working in this clone")
        sys.exit(whoami(ap.parse_args(sys.argv[2:]).name))
    elif cmd == "attribute":
        ap = argparse.ArgumentParser(prog="kit.py attribute")
        ap.add_argument("name")
        ap.add_argument("--apply", action="store_true")
        a = ap.parse_args(sys.argv[2:])
        sys.exit(attribute(a.name, a.apply))
    elif cmd == "check":
        problems = check()
        for p in problems:
            print(f"kit: PROBLEM: {p}")
        if problems:
            sys.exit(1)
        print("kit: check passed")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
