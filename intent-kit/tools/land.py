#!/usr/bin/env python3
"""Land a branch on main with plain git, following the project's landing policy.

  python intent-kit/tools/land.py [branch] [--no-push] [--dry-run]

- branch: defaults to the current branch.
- "landing": "linear" (intent-kit/config.json) rebases the branch onto main (intent-kit/tools/sync.py),
  then fast-forwards main to it: no merge commits, and each commit keeps the
  `Session:` trailer of the session that made it. "merge" merges the branch into main
  with a merge commit.
- Then, if "push_on_land" is on, pushes main to every configured remote. Local main is
  the source of truth: if a push fails, main keeps the work and the failure is reported.
- Checks before touching anything: the branch has new commits and its checkout has
  nothing uncommitted. On a conflict nothing changes; resolve and land again.

Land when the owner asks. Intent entries and current-view documents are already on
main (intent-kit/tools/to_main.py); landing carries everything else.

Managed by intent-kit.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import CFG, MAIN, REPO, TARGET, TOOLS_REL, checkout_of, current_branch, git, with_trailer  # noqa: E402
from sync import sync  # noqa: E402

TOOL = "land"


def fail(msg, code=1):
    print(f"{TOOL}: FAILED: {msg}", file=sys.stderr)
    sys.exit(code)


def g(*args, cwd=None, check=True, **kw):
    r = git(*args, cwd=cwd or MAIN, **kw)
    if check and r.returncode != 0:
        fail(f"git {' '.join(args)} failed:\n{r.stderr.strip() or r.stdout.strip()}")
    return r


def o(*args, cwd=None):
    return g(*args, cwd=cwd).stdout.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("branch", nargs="?")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    policy = CFG.get("landing", "linear")

    branch = a.branch or current_branch(REPO)
    if not branch or branch == TARGET:
        fail(f"name the branch to land (or run this on that branch, not on {TARGET})")
    if g("rev-parse", "--verify", "-q", f"refs/heads/{branch}^{{commit}}", check=False).returncode:
        fail(f"no local branch {branch!r}")

    commits = o("log", "--reverse", "--format=%h %s", f"{TARGET}..{branch}")
    if not commits:
        print(f"{TOOL}: nothing to land: {branch} has no commits that {TARGET} lacks")
        return
    wt = checkout_of(branch)
    if wt and o("status", "--porcelain", cwd=wt):
        fail(f"{branch} has uncommitted changes in {wt}; they would not be landed. Commit them first.")
    behind = int(o("rev-list", "--count", f"{branch}..{TARGET}"))
    if policy == "linear" and behind and not wt:
        fail(f"{branch} is {behind} commit(s) behind {TARGET} and isn't checked out anywhere to rebase it")
    main_wt = checkout_of(TARGET)

    remotes = o("remote").split() if CFG.get("push_on_land", True) and not a.no_push else []
    n = len(commits.splitlines())
    print(f"{TOOL}: {branch} -> {TARGET} by {policy} ({n} commit(s)"
          f"{f', {behind} new on {TARGET}' if behind else ''})")
    print("\n".join(f"  {c}" for c in commits.splitlines()))
    if CFG.get("backplane") and "origin" in o("remote").split():
        print(f"{TOOL}: WARNING: a remote named 'origin' exists. Backplane branches new threads from "
              "origin's default branch, not local main. Rename it (git remote rename origin <name>).")
    if a.dry_run:
        print(f"{TOOL}: dry run; would land, then push to: {', '.join(remotes) or '(none)'}")
        return

    old = o("rev-parse", TARGET)
    if policy == "linear":
        if behind and not sync(wt):
            fail(f"rebase onto {TARGET} failed; nothing was changed (see above)")
        if main_wt:
            r = g("merge", "--ff-only", branch, cwd=main_wt, check=False)
            if r.returncode != 0:
                fail(f"fast-forward failed; {TARGET} is unchanged:\n{r.stderr.strip() or r.stdout.strip()}")
        else:
            tip = o("rev-parse", branch)
            if g("merge-base", "--is-ancestor", old, tip, check=False).returncode != 0:
                fail(f"{branch} is not on top of {TARGET}; sync it first")
            g("update-ref", "-m", f"{TOOL}: fast-forward to {branch}", f"refs/heads/{TARGET}", tip, old)
    else:
        msg = with_trailer(f"Merge branch '{branch}'")
        if main_wt:
            r = g("merge", "--no-ff", "-m", msg.rstrip(), branch, cwd=main_wt, check=False)
            if r.returncode != 0:
                g("merge", "--abort", cwd=main_wt, check=False)
                fail(f"merge failed; {TARGET} is unchanged:\n{r.stderr.strip() or r.stdout.strip()}")
        else:
            r = g("merge-tree", "--write-tree", "--name-only", "--no-messages", TARGET, branch, check=False)
            if r.returncode != 0:
                files = "\n  ".join(r.stdout.strip().splitlines()[1:])
                fail(f"{branch} conflicts with {TARGET} in:\n  {files}\nNothing was changed. "
                     f"Sync the branch ({TOOLS_REL}/sync.py), resolve, and land again.")
            new = g("commit-tree", r.stdout.split()[0], "-p", old, "-p", branch, "-F", "-",
                    input=msg, env=dict(os.environ)).stdout.strip()
            g("update-ref", "-m", f"{TOOL}: merge {branch}", f"refs/heads/{TARGET}", new, old)
    print(f"{TOOL}: {TARGET} is now at {o('rev-parse', '--short', TARGET)}")

    failed = []
    for rem in remotes:
        p = g("push", rem, f"{TARGET}:{TARGET}", check=False)
        print(f"{TOOL}: push {rem}: {'ok' if p.returncode == 0 else 'FAILED'}")
        if p.returncode != 0:
            failed.append(rem)
            print("  " + (p.stderr.strip() or p.stdout.strip()).replace("\n", "\n  "), file=sys.stderr)
    if not remotes:
        print(f"{TOOL}: landed locally only")
    if CFG.get("backplane"):
        print(f"{TOOL}: settle the thread in Backplane (it does not see local merges).")
    if failed:
        fail(f"landed locally, but pushing to {', '.join(failed)} failed (see above)", code=2)


if __name__ == "__main__":
    main()
