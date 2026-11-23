#!/usr/bin/env python3
"""Bring this branch up to date with main.

  python tools/sync.py [--quiet]

Run at the start of a session in a worktree, or on any branch other than main. If
the branch has no commits of its own it fast-forwards to main. Otherwise it follows
the project's landing policy (intent-kit.json "landing"): "linear" rebases the
branch's commits onto main, "merge" merges main into the branch. Uncommitted changes
are stashed and restored around it. On a conflict nothing is changed and the
conflicting files are listed: resolve by hand or ask the owner.

Managed by intent-kit.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import CFG, REPO, TARGET, current_branch, git  # noqa: E402


def _count(rng, cwd):
    return int(git("rev-list", "--count", rng, cwd=cwd).stdout.strip() or 0)


def sync(cwd=REPO, quiet=False) -> bool:
    """Bring the branch checked out in `cwd` up to date with main. True if it now has main."""
    say = (lambda *_: None) if quiet else print
    branch = current_branch(cwd)
    if not branch or branch == TARGET:
        say(f"sync: on {branch or 'a detached HEAD'}; nothing to do")
        return True
    if git("rev-parse", "--verify", "-q", TARGET, cwd=cwd).returncode != 0:
        say(f"sync: no {TARGET} branch yet; nothing to do")
        return True
    behind = _count(f"{branch}..{TARGET}", cwd)
    if not behind:
        say(f"sync: {branch} already has everything on {TARGET}")
        return True
    ahead = _count(f"{TARGET}..{branch}", cwd)
    if not ahead:
        r = git("merge", "--ff-only", "--autostash", TARGET, cwd=cwd)
        how, abort = "fast-forwarded to", None
    elif CFG.get("landing") == "merge":
        r = git("merge", "--no-edit", "--autostash", TARGET, cwd=cwd)
        how, abort = "merged", ("merge", "--abort")
    else:
        r = git("rebase", "--autostash", TARGET, cwd=cwd)
        how, abort = f"rebased {ahead} commit(s) onto", ("rebase", "--abort")
    if r.returncode != 0:
        files = git("diff", "--name-only", "--diff-filter=U", cwd=cwd).stdout.split()
        if abort and files:
            git(*abort, cwd=cwd)
        print(f"sync: FAILED: {branch} conflicts with {TARGET}"
              + (" in:\n  " + "\n  ".join(files) if files else f":\n{r.stderr.strip() or r.stdout.strip()}")
              + "\nNothing was changed. Resolve by hand, or ask the owner.", file=sys.stderr)
        return False
    say(f"sync: {how} {TARGET} ({behind} new commit(s) from {TARGET})")
    return True


if __name__ == "__main__":
    sys.exit(0 if sync(quiet="--quiet" in sys.argv) else 1)
