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

## Onboarding

- **R-005 (target).** An onboarding phase asks the owner about the configuration and
  records the answers so the repository respects them. [I-0003] Which options it asks
  about is still open (see the vision).

## Parallel work

- **R-006 (hard).** Capturing intent, or creating any numbered entry, from a worktree or
  branch never produces colliding numbers. [I-0002]
- **R-007 (hard).** Numbers are sequential, and entries are committed to main when
  captured. [I-0003]
- **R-008 (expectation).** Intent captured in a worktree that never lands remains on
  main. [I-0004]

## The record

- **R-009 (hard).** The session record is always a separate repository, never inside the
  project repository. [I-0004]
- **R-010 (target).** The record can have a remote and be merged, pushed and pulled.
  [I-0004]

## The intent log

- **R-011 (hard).** Project intent and method intent go in one log, with no marks or
  separation. [I-0005]
