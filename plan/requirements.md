# Requirements

Current projection of the [vision](../intent/vision.md) into checkable statements.
Current view only: no history sections. Each item cites its source. Numbers come from
the owner's words where they gave one; where the vision is vaguer, the requirement says
so instead of inventing a number. IDs are stable: a requirement keeps its number when
others are added or removed.

**Firmness:**
- **hard:** the project fails if it doesn't meet this.
- **target:** aimed for; missing it needs a reason and the owner's agreement.
- **expectation:** the owner's expected or hoped-for outcome, explicitly not a hard line.
- **illustrative:** an example the owner gave to make the idea concrete. Not a requirement;
  listed so it isn't mistaken for one.

## The package

- **R-001 (hard).** Brings a new project, or an existing one not yet run this way, into
  the method, and can be imported into other projects. [I-0001]
- **R-002 (hard).** Adopting an existing project overwrites none of its files. Anything
  that can't be merged safely stops the run before anything changes. Derived from R-001:
  an existing project must survive being imported into.
- **R-003 (hard).** Includes a clean, written version of the philosophy, not the spoken
  transcripts. [I-0001]
- **R-004 (hard).** Includes the scripts for session capture and verbatim intent
  extraction, with the improvements found in earlier use. [I-0001]

- **R-012 (hard).** What ships contains no record of developing the kit: a new project's
  intent log, decisions and lessons start empty. [I-0006]
- **R-013 (target).** The working rules reach a project as a file its `CLAUDE.md`
  imports, not as text written into `CLAUDE.md`. [I-0006]

## Onboarding

- **R-005 (target).** An onboarding phase asks the owner about the configuration and
  records the answers so the repository respects them. [I-0003] Which options it asks
  about is still open (see the vision).
- **R-014 (hard).** Onboarding answers are cited from the configuration, by session and
  message, and aren't added to the project's intent log. [I-0006]
- **R-018 (target).** Onboarding checks for a Python that can run the tools before
  setting anything up, and stops if there isn't one. [I-0008]
- **R-019 (target).** Onboarding asks where the record lives, and allows an existing git
  remote, a newly created one, or local only with no remote. [I-0008, I-0009]

## Parallel work

- **R-006 (hard).** Capturing intent, or creating any numbered entry, from a worktree or
  branch never produces colliding numbers. [I-0002]
- **R-007 (hard).** Numbers are sequential, and entries are committed to main when
  captured. [I-0003]
- **R-008 (expectation).** Intent captured in a worktree that never lands remains on
  main. [I-0004]
- **R-015 (hard).** Committing to main doesn't rewrite the session's branch unless the
  project opts in. [I-0007]
- **R-016 (hard).** Adopting an existing repository adds nothing that changes how git
  treats the files already there (line endings, ignore rules for its folders). Those are
  suggested instead. [I-0007]
- **R-017 (hard).** The "already captured" check matches whole messages and errs toward
  showing a message as uncaptured. [I-0007]

## The record

- **R-009 (hard).** The session record is always a separate repository, never inside the
  project repository. [I-0004]
- **R-010 (target).** The record can have a remote and be merged, pushed and pulled.
  [I-0004]
- **R-020 (hard).** A record with no remote is a supported setup: nothing reports it as
  a problem or prompts to add one. [I-0009]
- **R-021 (hard).** Record remotes work with any git server, through plain git. The kit
  uses no host-specific tool, `gh` included. [I-0009]
- **R-022 (target).** When a likely secret reaches the record, the owner is reminded,
  and keeps being reminded until it's dealt with. [I-0010]
- **R-023 (target).** On the owner's request, a secret can be removed from the record's
  files and from all of its history. Nothing is scrubbed without a request. [I-0010]
- **R-024 (hard).** Sessions sharing a checkout commit their own record files
  independently, without dropping or absorbing each other's commits. [I-0010]
- **R-025 (hard).** The commit hook runs on every platform git does: git's copy of it is
  executable. Derived from R-001: a project must work when cloned elsewhere.
- **R-026 (expectation).** Pushing the record is manual. The record's size is accepted
  as it is. [I-0010]

## The intent log

- **R-011 (hard).** Project intent and method intent go in one log, with no marks or
  separation. [I-0005]
- **R-037 (target).** An intent entry that can't be understood without the agent's
  questions includes them, marked as not intent. One that makes sense on its own doesn't.
  Which applies is a judgment call each time, not a fixed rule. [I-0014]

## Authorship

- **R-027 (hard).** Every intent entry records the person whose words it is, including
  intent that agrees with or is unrelated to other intent. [I-0011]
- **R-028 (hard).** Every session in the record is attributed to one person. [I-0011,
  I-0013]
- **R-029 (target).** Decisions say who agreed to them, and lessons who found the
  problem. [I-0011, I-0013]
- **R-030 (expectation).** Attribution is taken on trust: no signatures or verification.
  [I-0011]
- **R-031 (target).** Onboarding asks what to call the person, offering a default
  inferred from Claude Code's settings that can usually just be accepted. [I-0012]
- **R-032 (hard).** Relayed intent records both the speaker and the person whose wishes
  it claims. Words are never recorded as anyone but the speaker's, and a relayed wish
  counts as the speaker's view of what the other person wants. [I-0012, I-0013]
- **R-033 (hard).** Requirements and the vision are written as the consensus and name no
  one. Where intent differs, the vision names who holds each view. [I-0012]
- **R-034 (hard).** Agreeing with intent is a new entry. [I-0012]
- **R-035 (expectation).** A session is never shared by two people or taken over.
  [I-0013]
- **R-036 (target).** Entries from before authorship are attributed only with their
  author's approval, by adding a header line, never by changing the words. The kit's own
  are attributed to the owner. [I-0012, I-0013]
