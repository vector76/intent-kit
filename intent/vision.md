# Vision

The current view of what intent-kit is. It is a synthesis built from the
[intent log](log/). The log is the authority and this document is a reading of it.

**Rules for this document:**
- Only what is believed **now**. There are no superseded sections, strike-throughs or
  changelogs. Git holds the history.
- Rationale is kept only where a point would otherwise look wrong or strange, and
  then as a short reason ("because E-0004 showed …"), not as a story.
- Each point cites the intent entries it rests on.
- Open questions are part of the current view, so they belong here. Settled
  history does not.

---

## What it is

A reusable package that brings a project into traceable, intent-driven development. That
means intent recorded verbatim, projected into a current vision and plan, with every
output traced back to its session and a private record of the sessions themselves. It
works for new projects and for existing ones not yet run this way, and it can be
imported into them. [I-0001]

It distills the machinery first built for earlier projects (the intent log, the
requirements, session recording and the scripts behind them), including the
improvements found while using it. [I-0001] Improvements go from the kit to projects
(by upgrading them). A fix found while working in a project doesn't have to be fed back
into the kit directly. [I-0008]

## What it contains

The kit ships **projected documents and tools, not a record**: how-to instructions,
recipes and scripts that a project's `CLAUDE.md` links to. The kit's own intent,
decisions and lessons matter for developing the kit, but they don't go into a project,
which starts its own record empty. [I-0006]

- **A clean write-up of the philosophy.** The owner first laid it out as spoken,
  transcribed prompts, full of speech-to-text slips. The kit has it as a neat document
  that a new project starts from. [I-0001]
- **Templates and scripts**: the folder structure, starter documents and the Python
  tools that capture sessions and intent. [I-0001] The intent extractor reads Claude
  Code's transcript files, whose format isn't documented. That's accepted for now.
  [I-0008]
- **Rules linked into `CLAUDE.md`**, not dropped into it. The working rules are a
  generated file the project's `CLAUDE.md` imports, so `CLAUDE.md` stays the project's
  own. [I-0006]
- **An onboarding phase.** When a project is first brought in, the owner answers a set of
  configuration questions, and the answers are recorded so the repository respects them.
  [I-0003] The answers are cited from the configuration, not entered as the project's
  intent: a project's log doesn't open with record-keeping. [I-0006] Setup choices the
  owner changes later are captured as intent like anything else. [I-0005] Onboarding
  checks that Python is available, since the tools need it. It also asks where the
  record lives: an existing git remote, a new one created then, or none. [I-0008]

## How it handles parallel work

- **It is worktree-aware in general**, not only for one tool. Any session may run in a
  worktree (Claude Code's, Backplane's or the owner's own), and capturing intent there
  must not cause collisions or tangle the numbering. [I-0002] Backplane is what first
  forced the issue, but the owner wasn't seeking worktrees out. [I-0002]
- **Numbers are sequential, and entries are committed to main when they're captured.**
  [I-0003]
- **Intent captured in a worktree that never lands still reaches main.** That's accepted:
  most worktrees will land. [I-0004]
- **A branch isn't synced automatically when something goes to main.** A project can opt
  in. [I-0007] Syncing rewrites a linear branch, which would force-push any branch that's
  already pushed or has a pull request.

## The record of sessions

- **It is always a separate repository**, never part of the project repo, to reduce the
  chance of leaking something by accident. [I-0004]
- **It can still have a remote**, so one or more people can merge, push and pull it for
  traceability and after-the-fact review. [I-0004]
- **Keeping it local, with no remote, is a full option**, not a step short of having one.
  It's somewhat safer for privacy. [I-0009]
- **A remote can be on any git server.** It doesn't mean GitHub, and the kit doesn't use
  GitHub's `gh` tool. [I-0009]
- **Pushing the record is manual**, and that's fine. [I-0010]
- **Its size is accepted.** Transcripts, subagent transcripts included, make it grow
  quickly. [I-0010]
- **If secrets appear in it, the owner is reminded, and its history can be scrubbed on
  request.** [I-0010]
- **Sessions sharing a checkout commit to the record independently.** Each has its own
  session id and its own files there. [I-0010]

## Intent about the method

- **Intent about the project and intent about the recording method share one log**, with
  no marks or separation. [I-0005] If a clean, project-only rendering of the intent is
  ever wanted, it can be produced from the log on request. That isn't planned or
  suggested; it's just available. [I-0005]

## Open questions and tensions

- **Which configuration options onboarding should offer.** The owner named the record's
  location as one, then made it fixed (I-0004), and didn't know the others offhand
  (I-0003). The current set (visibility, layers, stances, landing policy, push on landing,
  agents, Backplane, tools folder) was proposed by the agent and accepted in passing
  ("everything else I think makes sense", I-0004). It hasn't been confirmed item by item.
- **The kit's own settings are the kit's defaults, not the owner's choices.** That covers
  visibility (confidential), landing (linear) and the rest. Whether the kit may ever be
  published is open, as is its name: "intent-kit" is a placeholder.
- **Moving the existing projects onto the kit.** Projects already using the earlier
  version of the machinery could be upgraded to it, or left as they are. The owner has
  asked what migrating would gain (I-0008) and hasn't decided.
