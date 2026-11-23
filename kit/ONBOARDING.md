# Onboarding a project

Instructions for the agent that brings a project into this method, new or existing.
The owner usually starts it by saying something like *"set this project up with the
intent kit at `<kit>`; read its ONBOARDING.md"*, where `<kit>` is this folder. Run the
session **in the project's own folder** (its main checkout), so the session's transcript
belongs to that project.

Read [PHILOSOPHY.md](PHILOSOPHY.md) first. You'll be explaining it.

What the project gets is the method, not a history: the tools, the starter documents,
`METHOD.md` (the philosophy) and a generated `METHOD-RULES.md` that its `CLAUDE.md`
imports. Its intent log, decisions and lessons start empty, and fill with its own.

## 1. Look before asking

- Is the folder empty, or an existing repository? Is it the main checkout and not a
  worktree (`git rev-parse --git-common-dir`)? Which branch is the main one?
- Is there already a `CLAUDE.md`, `.claude/settings.json`, `.gitignore`, `tools/` folder,
  `core.hooksPath` or `.git/hooks/prepare-commit-msg`? The bootstrap merges into the
  first three and stops on the rest. A dry run (step 3) lists what's in the way.
- Remotes: is any of them public? Does the project use worktrees (`git worktree list`),
  Claude Code's or Backplane's (`.backplane/`)?
- For an existing project: are there earlier Claude sessions in this folder? They're
  in `~/.claude/projects/<folder name with every non-alphanumeric character as ->/`.

## 2. Ask the owner

Ask conversationally, a few questions at a time, and say what each choice changes. Let
the owner answer in their own words: the answers are cited from the config by session
and message, so their exact words stay in the record. Don't fill answers in for them.
Where there's a default, say what it is.

| Choice | Options | What it changes |
|---|---|---|
| Name and a one-line summary | free text | README, CLAUDE.md, vision heading |
| Visibility | **confidential** (default) or publishable | Privacy rule: confidential means no public remote and generic web queries; publishable means keeping personal details and home-directory paths out of the repo |
| Layers | any of research (N-), concepts (C-), experiments (E-) | Folders, numbered kinds, and the rules that go with them |
| Stances | wide-search, forward-plausibility, or none | Extra rules: don't narrow the search early; judge plausibility by enabling milestones rather than consensus |
| Landing | **linear** (rebase and fast-forward, default) or merge | How `land.py` and `sync.py` behave |
| Push on landing | **yes** (default) or no | Whether `land.py` pushes main to every remote |
| Agents | **Claude only** (default) or any | Other agents leave no transcript; the rule says so |
| Backplane | yes or **no** | Backplane-specific rules; skips its `[Backplane]` reports when extracting intent |
| Tools folder | **tools** (default) | Use another (`tools/kit`) if `tools/` holds files of the same names |

Some things are fixed, not choices; say so if they come up:
- **The record is always a separate private git repo** (`record/`, ignored by the
  project). It can have its own private remote.
- **Numbered entries are sequential and committed to main when created.** This works the
  same in worktrees, on branches and in a single checkout.

## 3. Dry run, then bootstrap

```
python <kit>/bootstrap.py init <project> --name "..." --summary "..." \
    [--visibility publishable] [--layers research,experiments] [--stances wide-search] \
    [--landing merge] [--no-push] [--agents any] [--backplane] [--tools-dir tools/kit] --dry-run
```

Show the owner the list of what will be added and merged. Then run it again without
`--dry-run`.
- **New folder:** it runs `git init`, writes everything, creates `record/` as its own
  repo, sets `core.hooksPath` and commits the scaffold on main.
- **Existing repository:** it writes and merges but doesn't commit. Its `CLAUDE.md` keeps
  everything it had, plus a short section ending in `@METHOD-RULES.md`. Show
  `git status`. With the owner's OK, commit the scaffold on the main branch.

The hooks take effect from the **next** session in this folder. This session's transcript
is still picked up: the next session's start, or a sweep, copies it.

## 4. Record the answers in the config, not the intent log

Setting the project up isn't intent about the project, so the onboarding answers don't
become intent entries. The config cites them instead:

```
python tools/capture_session.py --all --commit            # this and any earlier sessions into the record
python tools/extract_human_messages.py <this session id> --list
python tools/kit.py cite <this session id> --msg 3 --keys visibility
python tools/kit.py cite <this session id> --msg 4 5 --keys layers,landing
```

The session id is in the `CLAUDE_CODE_SESSION_ID` environment variable. `cite` records
each message's session and timestamp under `"sources"` in `intent-kit.json`. Then
`--list` marks those messages `c`.

The project's intent log starts with **the owner's first words about the project
itself**. If they've already said what it is in this session, capture those messages:

```
python tools/extract_human_messages.py <this session id> --slug first-braindump --msg 6 7
```

If they haven't, ask for their first braindump and capture it the same way. A message
that mixes setup answers with intent about the project is intent: capture it, and cite
its entry id for the setting as well. Re-run `--list` and check that every message is
marked (`*` or `c`) or isn't intent ("go ahead", "looks good").

Then:
- Write `intent/vision.md` from the entries, with each point citing its source and any
  contradictions under *Open questions and tensions*.
- `python tools/to_main.py docs -m "Vision and config from onboarding"`.
- `python tools/kit.py check` must pass.

## 5. Existing projects: history

- **Earlier sessions** were swept into the record in step 4. Their messages can be
  listed with the extractor (`--list` takes a session id or a path to a `.jsonl`). Offer
  the owner a backfill: list the earlier sessions' messages and let the owner pick which
  ones become entries. Don't capture old messages without the owner choosing them. Old
  intent may well be superseded.
- **Existing documents** (specs, READMEs, issue trackers) aren't intent: they're
  someone's projection of it. The vision can cite them as context. If the owner says "yes,
  that's still what I want", that statement is the intent entry.
- **Code that already exists** is an artifact. Commits made before onboarding have no
  `Session:` trailer, and that's fine.

## 6. Later

- **Changing a choice.** This is intent, mixed in with everything else the owner says
  while working: capture it as an entry, as with any intent. Then edit `intent-kit.json`
  and add the entry's id under `"sources"`, e.g. `"landing": ["I-0012"]`. Run
  `tools/kit.py render` and publish with `to_main.py docs`. If a layer is turned on,
  `python <kit>/bootstrap.py upgrade <project> --apply` adds its starter files.
- **A new kit version.** `python <kit>/bootstrap.py upgrade <project>` shows how the
  managed files (tools, commit hook, METHOD.md) differ, and `--apply` updates them and
  re-renders `METHOD-RULES.md`. It never touches the project's own content.
- **A record remote.** `git -C record remote add <name> <private url>`, then push and pull
  the record like any repo.
