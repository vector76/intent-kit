# How this project keeps its record

<!-- Generated from intent-kit.json by tools/kit.py render, and imported by CLAUDE.md. Change the config and re-render; edits made here are overwritten. -->

Intent is recorded verbatim, projected into a current vision and plan, and corrected by what the work teaches; every output traces back to the session that made it and the intent in force at the time. `METHOD.md` explains why. Read `intent/vision.md` before any work.

## Layers and IDs

| Layer | Where | IDs | Mutability |
|---|---|---|---|
| Intent (people's own words, verbatim, each naming its author) | `intent/log/` | I-0001 | append-only, never edit |
| Vision (current view) | `intent/vision.md` | — | rewritten to stay current |
| Requirements | `plan/requirements.md` | R-001 | current view only |
| Decisions | `plan/decisions/` | D-0001 | a decision can be replaced by a new one |
| Lessons (postmortems) | `plan/lessons/` | L-0001 | append-only |
| Raw sessions, candid notes | `record/` (separate private git repo) | session id | append-only |

Cite IDs wherever something is derived: requirements cite I- entries, decisions cite I-/R-.

## Rules

1. **Intent is people's own words, verbatim and append-only.** Never edit or paraphrase `intent/log/`. Capture new intent with `python tools/extract_human_messages.py <session-id> --slug <name> --msg <n> [...]` (see `intent/README.md`); it commits the entry to main at once. Intent about how the project is run and recorded is intent too, and goes in the same log. When someone states, refines or changes intent, capture it before the session ends, then update `intent/vision.md` (and `plan/requirements.md` if affected). **Before ending a session, run `--list` again: every message not marked `*` that states, refines or changes intent needs an entry.** Count; don't trust the filter.
2. **Current-view documents carry no history.** `intent/vision.md` and `plan/requirements.md` say only what is true now: no "superseded" or "previously" sections, no changelogs, no strike-throughs. Git is the history. Keep a short reason only where a point would otherwise look wrong ("because E-0004 showed ...").
3. **Every entry says according to whom.** An intent entry's `author:` is the person who typed the words. A session is one person's (it can't be shared or handed over), and the extractor takes the author from it. Never record words as anyone else's. When someone relays another person's wishes ("Alice wants X"), capture it with `--on-behalf-of Alice`: it stays the speaker's entry, and it counts as the speaker's view of what that person wants, not as their intent, until they say it themselves. Agreeing is a new entry by the person who agrees. A decision says who agreed to it (`agreed_by:`), and a lesson who found the problem (`found_by:`). This isn't proof of identity; it's so people know whom to talk to.
4. **Surface contradictions; don't resolve them silently.** If intent entries conflict, or a request conflicts with the vision, list it under *Open questions and tensions* in `intent/vision.md` and ask. Don't pick a side on your own. The vision and requirements are written as the consensus and name no one. Where people's intent differs, the open question names who holds each view, so they can talk it through; never decide between people.
5. **Read `plan/lessons/` before related work.** When a mistake is found, write an L- entry: what happened, which session and commit, root cause, how to avoid it. If the fix is a rule, add it to CLAUDE.md (METHOD-RULES.md is generated and would lose it).
6. **Confidential.** This repository is never published: no public remote, no sharing. When searching the web or using outside services, ask generic questions about the subject, and never describe the project's concept, design or goals in a query or request.
7. **The record is private and separate.** `record/` is its own git repository, ignored by this one. It holds raw transcripts (system prompts, file contents, personal details). Never copy its raw content into this repo, never add it to this repo, and never push it anywhere the owner hasn't set up. It may have its own private remote.

## Branches and worktrees

Work may happen in git worktrees (Claude Code's, Backplane's or your own) or on branches. The record stays consistent like this:

- **Numbered entries go straight to main when they are created**, whatever branch or worktree you are in. `extract_human_messages.py` does this for intent; `python tools/to_main.py <kind> --slug <name> --file <draft.md>` does it for decisions, lessons (kinds: decision, lesson). Write the draft outside tracked files (a temp or scratch folder) with `{ID}` where the number goes. The tool takes the next free number from main under a lock shared by every worktree and commits only that file. Never number an entry by hand. Your branch doesn't get the entry until it next syncs, and doesn't need it: numbers come from main.
- **Current-view documents go to main right after you edit them:** `intent/vision.md`, everything under `plan/`, `CLAUDE.md`, `intent-kit.json` and `METHOD-RULES.md`. Run `python tools/to_main.py docs -m "<what changed>"`. If main's copy changed in a conflicting way, nothing is copied and the conflict is reported. That usually means two threads disagree: tell the owner rather than resolving it.
- **Everything else waits for landing:** `python tools/land.py [branch]` rebases it onto main and fast-forwards main, never a merge commit. Then it pushes main to every remote. Land when the owner asks. Intent captured in a worktree that never lands is still on main; that's intended.
- At the start of a session in a worktree or on a branch other than main, run `python tools/sync.py` to bring it up to date. On a conflict it changes nothing; tell the owner.
- Before relying on a worktree's isolation, check `git worktree list`. In a checkout another agent may also be using, commit only your own paths (`git commit -- <paths>`), never `git commit -a` or `git add -A`.

## Session capture

Hooks in `.claude/settings.json` run `tools/capture_session.py`. It copies each session's transcript into `record/sessions/` (worktree sessions included) and commits the record repo at session start, every 10 turns and at session end. Sweep by hand with `python tools/capture_session.py --all --commit`. Commits here get a `Session: <id>` trailer from `.githooks/prepare-commit-msg` (enabled by `git config core.hooksPath .githooks`), linking each commit to the session that made it; don't remove it. If the session start says this clone doesn't know who is working in it, ask the person what to call them before other work, suggest the name it offers, and run `python tools/kit.py whoami --set "<name>"` with the name they give. `python tools/kit.py check` verifies the whole setup. If the session start says the session is NOT being recorded, tell the owner. On a fresh clone the fix is usually `git config core.hooksPath .githooks` and `python tools/kit.py record --remote <the record's private url>`.

**Secrets in the record.** Transcripts keep whatever passed through a session, keys and passwords included. The hooks scan new text for likely secrets. If the session start says the record holds some, tell the owner, show them the masked list (`python tools/record_secrets.py`), and suggest revoking any real one. Scrubbing rewrites the record's history (`python tools/record_secrets.py scrub <id>`), so do it only when the owner asks. Never print, repeat or search for a secret's full text: it would land in this session's transcript too.

Use Claude as the agent here: other agents leave no Claude transcript, so their sessions would be missing from the record.

When extracting intent from a forked or resumed session, the handed-over context at the start shows up as messages but is already captured (marked `*`) or isn't the owner's words: skip it.

## Numbering

IDs are sequential within their folder and are assigned by the tools above, from main. Requirements (R-) are numbered by hand in `plan/requirements.md`, which is a current-view document, and keep their number when others are added or removed.

## Where the project's setup came from

The choices in `intent-kit.json` cite what set them under `"sources"`. The owner's answers at onboarding are cited by session and message (the words are in the record), not captured as intent: setting the project up isn't intent about the project. A change the owner asks for later is captured as intent like anything else, then cited by its I- id: `python tools/kit.py cite <session-id> --msg <n> --keys <setting>` or edit the config by hand.
