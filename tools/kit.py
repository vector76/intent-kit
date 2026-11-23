#!/usr/bin/env python3
"""Keep this project's intent-kit setup honest.

  python tools/kit.py render    regenerate METHOD-RULES.md from intent-kit.json, and make
                                sure CLAUDE.md imports it
  python tools/kit.py check     verify the setup; exit 1 if anything is wrong
  python tools/kit.py cite <session-id> --msg N [N ...] --keys visibility,layers
                                record which of the owner's messages set those choices

METHOD-RULES.md is generated: to change how the project is run, change intent-kit.json
(citing what asked for it under "sources"), re-render, and publish both with
`tools/to_main.py docs`. CLAUDE.md stays the project's own; it holds one
`@METHOD-RULES.md` line, which Claude Code reads as an import.

The owner's onboarding answers are cited from the config (`cite`), not captured as
intent entries: setting the project up isn't intent about the project. Changes the
owner asks for later are captured as intent like anything else, and cited by entry id.

Managed by intent-kit.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import (CONFIG_NAME, DEFAULTS, MAIN, RECORD, REPO, TARGET, git, kinds,  # noqa: E402
                    load_config, main_tree_files, record_problem)

RULES_NAME = "METHOD-RULES.md"
IMPORT = "@" + RULES_NAME
BEGIN = "<!-- intent-kit:begin -->"  # an older kit inlined the rules in CLAUDE.md between these
END = "<!-- intent-kit:end -->"
MANAGED = ["kitlib.py", "capture_session.py", "extract_human_messages.py", "to_main.py",
           "sync.py", "land.py", "kit.py"]
CLAUDE_POINTER = (
    "## How this project keeps its record\n\n"
    "This project follows the intent-kit method: `METHOD.md` explains it, and the working rules "
    "below are generated into `METHOD-RULES.md` from `intent-kit.json`. Project-specific rules "
    "belong in this file, not that one.\n\n" + IMPORT + "\n")


def render_rules(cfg: dict) -> str:
    t = cfg.get("tools_dir", "tools")
    layers = cfg.get("layers", [])
    stances = cfg.get("stances", [])
    k = kinds(cfg)
    rows = [
        ("Intent (the owner's words, verbatim)", "`intent/log/`", "I-0001", "append-only, never edit"),
        ("Vision (current view)", "`intent/vision.md`", "—", "rewritten to stay current"),
        ("Requirements", "`plan/requirements.md`", "R-001", "current view only"),
        ("Decisions", "`plan/decisions/`", "D-0001", "a decision can be replaced by a new one"),
        ("Lessons (postmortems)", "`plan/lessons/`", "L-0001", "append-only"),
    ]
    if "research" in layers:
        rows.append(("Research (what's known outside this project)", "`research/`", "N-0001",
                     "a note can be corrected; cite sources"))
    if "concepts" in layers:
        rows.append(("Concepts (candidate designs, hypotheses)", "`concepts/`", "C-0001",
                     "revised in place; set aside, not deleted"))
    if "experiments" in layers:
        rows.append(("Experiments (builds, tests, calculations, models)", "`experiments/`", "E-0001",
                     "the record of a question and its answer"))
    rows.append(("Raw sessions, candid notes", "`record/` (separate private git repo)", "session id",
                 "append-only"))
    table = "| Layer | Where | IDs | Mutability |\n|---|---|---|---|\n" + "\n".join(
        f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows)

    sources = "I-" + "".join(f"/{p}-" for p in (["E"] if "experiments" in layers else [])
                             + (["N"] if "research" in layers else []))
    cite = (f"Cite IDs wherever something is derived: requirements cite {sources} entries, "
            f"decisions cite {sources}/R-")
    cite += ", and experiments cite the question they answer." if "experiments" in layers else "."

    rules = [
        "**Intent is the owner's words, verbatim and append-only.** Never edit or paraphrase "
        f"`intent/log/`. Capture new intent with `python {t}/extract_human_messages.py <session-id> "
        "--slug <name> --msg <n> [...]` (see `intent/README.md`); it commits the entry to main at once. "
        "Intent about how the project is run and recorded is intent too, and goes in the same log. "
        "When the owner states, refines or changes intent, capture it before the session ends, then "
        "update `intent/vision.md` (and `plan/requirements.md` if affected). **Before ending a session, "
        "run `--list` again: every message not marked `*` that states, refines or changes intent needs "
        "an entry.** Count; don't trust the filter.",
        "**Current-view documents carry no history.** `intent/vision.md` and `plan/requirements.md` say "
        "only what is true now: no \"superseded\" or \"previously\" sections, no changelogs, no "
        "strike-throughs. Git is the history. Keep a short reason only where a point would otherwise "
        "look wrong (\"because E-0004 showed ...\").",
        "**Surface contradictions; don't resolve them silently.** If intent entries conflict, or a "
        "request conflicts with the vision, list it under *Open questions and tensions* in "
        "`intent/vision.md` and ask. Don't pick a side on your own.",
    ]
    if "wide-search" in stances:
        rules.append(
            "**Don't narrow the search early.** An example in the intent is an example. Don't turn one "
            "into a requirement or a decision without the owner saying so, and when presenting options, "
            "show the spread rather than converging on a favorite.")
    if "research" in layers:
        rules.append(
            "**Keep what's known apart from what's wanted.** Facts about the world go in `research/` with "
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
        "**Read `plan/lessons/` before related work.** When a mistake is found, write an L- entry: what "
        "happened, which session and commit, root cause, how to avoid it. If the fix is a rule, add it to "
        f"CLAUDE.md ({RULES_NAME} is generated and would lose it).")
    if cfg.get("visibility") == "publishable":
        rules.append(
            "**Publishable.** This repository is meant to be shareable. Keep personal details, account "
            "information, credentials and absolute paths under a home directory out of it. Anything too "
            "candid goes in the private record (`record/notes/`), with a neutral one-line pointer here.")
    else:
        rules.append(
            "**Confidential.** This repository is never published: no public remote, no sharing. When "
            "searching the web or using outside services, ask generic questions about the subject, and "
            "never describe the project's concept, design or goals in a query or request.")
    rules.append(
        "**The record is private and separate.** `record/` is its own git repository, ignored by this "
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
        f"you are in. `extract_human_messages.py` does this for intent; `python {t}/to_main.py <kind> "
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
                       f" once you've synced it (`python {t}/sync.py`).")
           if "experiments" in layers else ""),
        "**Current-view documents go to main right after you edit them:** `intent/vision.md`, everything "
        f"under `plan/`, `CLAUDE.md`, `{CONFIG_NAME}` and `{RULES_NAME}`. Run `python {t}/to_main.py docs -m \"<what "
        "changed>\"`. If main's copy changed in a conflicting way, nothing is copied and the conflict is "
        "reported. That usually means two threads disagree: tell the owner rather than resolving it.",
        f"**Everything else waits for landing:** `python {t}/land.py [branch]` {land}.{push} Land when "
        "the owner asks. Intent captured in a worktree that never lands is still on main; that's intended.",
        f"At the start of a session in a worktree or on a branch other than main, run `python {t}/sync.py` "
        "to bring it up to date. On a conflict it changes nothing; tell the owner.",
        "Before relying on a worktree's isolation, check `git worktree list`. In a checkout another agent "
        "may also be using, commit only your own paths (`git commit -- <paths>`), never `git commit -a` "
        "or `git add -A`.",
    ]
    branch_text = "\n".join(f"- {b}" for b in branches)

    capture = (
        f"Hooks in `.claude/settings.json` run `{t}/capture_session.py`. It copies each session's "
        "transcript into `record/sessions/` (worktree sessions included) and commits the record repo at "
        f"session start, every {cfg.get('record_commit_every', 10)} turns and at session end. Sweep by "
        f"hand with `python {t}/capture_session.py --all --commit`. Commits here get a `Session: <id>` "
        "trailer from `.githooks/prepare-commit-msg` (enabled by `git config core.hooksPath .githooks`), "
        "linking each commit to the session that made it; don't remove it. "
        f"`python {t}/kit.py check` verifies the whole setup.")
    if cfg.get("agents", "claude-only") == "claude-only":
        capture += ("\n\nUse Claude as the agent here: other agents leave no Claude transcript, so their "
                    "sessions would be missing from the record.")
    else:
        capture += ("\n\nOther agents may be used, but only Claude sessions are captured automatically. "
                    "For another agent's session, save what you can of it under `record/notes/`, and "
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
        "at the time. `METHOD.md` explains why. Read `intent/vision.md` before any work.",
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
            "other, into the one `record/`.",
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
              "Requirements (R-) are numbered by hand in `plan/requirements.md`, which is a current-view "
              "document, and keep their number when others are added or removed.",
              "", "## Where the project's setup came from", "",
              f"The choices in `{CONFIG_NAME}` cite what set them under `\"sources\"`. The owner's answers "
              "at onboarding are cited by session and message (the words are in the record), not captured "
              "as intent: setting the project up isn't intent about the project. A change the owner asks "
              "for later is captured as intent like anything else, then cited by its I- id: "
              f"`python {t}/kit.py cite <session-id> --msg <n> --keys <setting>` or edit the config by hand."]
    return "\n".join(parts) + "\n"


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
    print("kit: publish with tools/to_main.py docs" if changed else "kit: rules already current")
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
          "(publish with tools/to_main.py docs)")


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
    t = cfg.get("tools_dir", "tools")

    p = record_problem()
    if p:
        problems.append(p)
    if not (RECORD / ".git").exists():
        problems.append("record/ is not a git repository of its own (git init it, in the main checkout)")
    if git("config", "core.hooksPath", cwd=root).stdout.strip() != ".githooks":
        problems.append("core.hooksPath is not .githooks, so commits get no Session: trailer "
                        "(git config core.hooksPath .githooks)")
    if not (root / ".githooks" / "prepare-commit-msg").is_file():
        problems.append(".githooks/prepare-commit-msg is missing")
    for name in MANAGED:
        if not (root / t / name).is_file():
            problems.append(f"{t}/{name} is missing")
    try:
        hooks = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8")).get("hooks", {})
    except (OSError, json.JSONDecodeError):
        hooks = {}
    for event in ("SessionStart", "Stop", "SessionEnd"):
        cmds = [h.get("command", "") for grp in hooks.get(event, []) for h in grp.get("hooks", [])]
        if not any("capture_session.py" in c for c in cmds):
            problems.append(f".claude/settings.json has no {event} hook running capture_session.py")
    claude = root / "CLAUDE.md"
    text = claude.read_text(encoding="utf-8") if claude.is_file() else ""
    if with_import(text) != text:
        problems.append(f"CLAUDE.md doesn't import {RULES_NAME} (python {t}/kit.py render)")
    rules = root / RULES_NAME
    if not rules.is_file():
        problems.append(f"{RULES_NAME} is missing (python {t}/kit.py render)")
    elif rules.read_text(encoding="utf-8") != render_rules(cfg):
        problems.append(f"{RULES_NAME} is stale or was edited by hand (python {t}/kit.py render)")
    if not (root / "METHOD.md").is_file():
        problems.append("METHOD.md is missing (the kit's bootstrap.py upgrade restores it)")
    vision = root / "intent" / "vision.md"
    if not vision.is_file():
        problems.append("intent/vision.md is missing")
    elif "Open questions and tensions" not in vision.read_text(encoding="utf-8"):
        problems.append("intent/vision.md has no 'Open questions and tensions' section")

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
        if not main_tree_files("intent/log"):
            notes.append("no intent entries on main yet: capture the owner's first words about the project")
    else:
        notes.append(f"no {TARGET} branch yet: make a first commit")
    if not cfg.get("sources"):
        notes.append(f"{CONFIG_NAME} has no \"sources\": cite the owner's messages that set its choices "
                     f"(python {t}/kit.py cite ...)")
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
