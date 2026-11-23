#!/usr/bin/env python3
"""Commit the record of intent and the plan straight to main, from any branch or worktree.

  python tools/to_main.py docs -m "what changed"
  python tools/to_main.py decision   --slug short-name --file draft.md [-m "subject"]
  python tools/to_main.py lesson     --slug short-name --file draft.md [-m "subject"]
  python tools/to_main.py intent     --slug short-name --file draft.md [-m "subject"]
  python tools/to_main.py research | concept | experiment ...   (when those layers are on)

Numbered entries: the draft is written anywhere outside tracked files (out/ is
ignored) with `{ID}` wherever the entry's ID goes. Under a lock shared by every
worktree, this takes the next free number from main, writes the entry and commits
only that file to main, with this session's `Session:` trailer. If main is checked
out somewhere (usually the main checkout), the entry is written and committed there;
if not, it is committed to the main branch directly. This branch doesn't get the
entry until it next syncs (tools/sync.py), and doesn't need it: numbers come from main.
With "sync_after_to_main" on in intent-kit.json, this branch is synced at once. An experiment's
entry is its folder's README.md; the rest of the experiment is then worked on here.

Intent entries normally go through tools/extract_human_messages.py, which uses this
module; `intent` here is only for a hand-written neutral entry (see intent/README.md).

`docs` is for the current-view documents: intent/vision.md, everything under plan/,
CLAUDE.md and intent-kit.json. Edit them where you are, then run it. On main it just
commits them. On another branch it commits them there (and nothing else), then copies
that commit, and any earlier unlanded commits that touch only these documents, onto
main. If main's copy changed in a way that conflicts, nothing is copied and the
conflict is reported: usually two threads disagree, so tell the owner.

Managed by intent-kit.
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import (CFG, DOCS, MAIN, REPO, TARGET, checkout_of, current_branch, git,  # noqa: E402
                    is_doc, kinds, main_tree_files, with_trailer)
from sync import sync  # noqa: E402

TOOL = "to_main"


def fail(msg):
    sys.exit(f"{TOOL}: FAILED: {msg}")


def g(*args, cwd=None, check=True, **kw):
    return git(*args, cwd=cwd or MAIN, check=check, tool=TOOL, **kw)


class MainLock:
    """A lock file in the shared git dir, so it covers every worktree."""

    def __init__(self, timeout=60, stale=300):
        common = g("rev-parse", "--path-format=absolute", "--git-common-dir").stdout.strip()
        self.path = Path(common) / "intent-kit-main.lock"
        self.timeout, self.stale = timeout, stale

    def __enter__(self):
        deadline = time.time() + self.timeout
        while True:
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return self
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime > self.stale:
                        self.path.unlink()  # left by a crashed run
                        continue
                except FileNotFoundError:
                    continue
                if time.time() > deadline:
                    fail(f"{self.path} is held by another session; try again")
                time.sleep(0.5)

    def __exit__(self, *exc):
        self.path.unlink(missing_ok=True)


def main_exists() -> bool:
    return g("rev-parse", "--verify", "-q", f"refs/heads/{TARGET}", check=False).returncode == 0


def next_id(kind: str) -> str:
    folder, prefix, digits, _ = kinds()[kind]
    names = [p[len(folder) + 1:].split("/")[0] for p in main_tree_files(folder)]
    wt = checkout_of(TARGET)
    if wt and (wt / folder).is_dir():  # uncommitted ones where main is checked out
        names += [p.name for p in (wt / folder).iterdir()]
    nums = [int(m.group(1)) for n in names if (m := re.match(rf"{prefix}-(\d+)", n))]
    return f"{prefix}-{max(nums, default=0) + 1:0{digits}d}"


def commit_files_to_main(files: dict[str, str], message: str) -> str:
    """Add new files to main, committing only them. Caller holds MainLock. Returns the commit."""
    message = with_trailer(message)
    wt = checkout_of(TARGET)
    if wt:
        for rel in files:
            if (wt / rel).exists():
                fail(f"{rel} already exists in {wt}")
        for rel, text in files.items():
            dest = wt / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8", newline="\n")
        rels = list(files)
        g("add", "--", *rels, cwd=wt)
        r = g("commit", "-q", "-F", "-", "--", *rels, cwd=wt, check=False, input=message)
        if r.returncode != 0:
            g("reset", "-q", "--", *rels, cwd=wt, check=False)
            for rel in rels:
                (wt / rel).unlink(missing_ok=True)
            fail(f"commit to {TARGET}:\n{r.stderr.strip() or r.stdout.strip()}")
        return g("rev-parse", "HEAD", cwd=wt).stdout.strip()
    # main is not checked out anywhere: build the commit without touching any checkout
    if not main_exists():
        fail(f"there is no {TARGET} branch yet; make a first commit on it")
    old = g("rev-parse", TARGET).stdout.strip()
    fd, index = tempfile.mkstemp(prefix="intent-kit-index-")
    os.close(fd)
    os.unlink(index)
    env = {**os.environ, "GIT_INDEX_FILE": index}
    try:
        g("read-tree", TARGET, env=env)
        for rel, text in files.items():
            if g("cat-file", "-e", f"{TARGET}:{rel}", check=False).returncode == 0:
                fail(f"{rel} already exists on {TARGET}")
            blob = g("hash-object", "-w", "--stdin", input=text.replace("\r\n", "\n")).stdout.strip()
            g("update-index", "--add", "--cacheinfo", f"100644,{blob},{rel}", env=env)
        tree = g("write-tree", env=env).stdout.strip()
    finally:
        Path(index).unlink(missing_ok=True)
    new = g("commit-tree", tree, "-p", old, "-F", "-", input=message).stdout.strip()
    g("update-ref", "-m", f"{TOOL}: add {', '.join(files)}", f"refs/heads/{TARGET}", new, old)
    return new


def after_main_changed():
    """Sync this branch with main only if the project asked for it (sync rewrites a linear
    branch, which a pushed branch or open pull request would then need force-pushed)."""
    branch = current_branch(REPO)
    if not branch or branch == TARGET:
        return
    if CFG.get("sync_after_to_main"):
        sync(REPO)
    else:
        print(f"{TOOL}: {branch} doesn't have this yet, and doesn't need it to; "
              f"run tools/sync.py when you want it here")


def entry_path(kind: str, eid: str, slug: str) -> str:
    folder, _, _, is_dir = kinds()[kind]
    return f"{folder}/{eid}-{slug}/README.md" if is_dir else f"{folder}/{eid}-{slug}.md"


def add_entry(kind: str, slug: str, render, subject: str | None = None) -> str:
    """render(id) -> file text. Commits the new entry to main; returns its repo-relative path."""
    if kind not in kinds():
        fail(f"unknown kind {kind!r} (layers not enabled in intent-kit.json?)")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        fail("a slug is lowercase letters, digits and hyphens")
    with MainLock():
        eid = next_id(kind)
        rel = entry_path(kind, eid, slug)
        msg = (subject or f"Add {eid}: {slug}").replace("{ID}", eid)
        sha = commit_files_to_main({rel: render(eid)}, msg)
    print(f"{TOOL}: committed {rel} to {TARGET} ({sha[:9]})")
    after_main_changed()
    return rel


def copy_to_main(commit: str) -> str:
    """Apply one commit's change onto main without touching other files where main is
    checked out. Caller holds MainLock. Returns the new main commit, or exits on a conflict."""
    paths = g("diff-tree", "--no-commit-id", "--name-only", "-r", commit).stdout.split()
    wt = checkout_of(TARGET)
    if wt and g("status", "--porcelain", "--", *paths, cwd=wt).stdout.strip():
        fail(f"{wt} (on {TARGET}) has uncommitted edits to {', '.join(paths)}; nothing was copied")
    old = g("rev-parse", TARGET).stdout.strip()
    r = g("merge-tree", "--write-tree", "--name-only", "--no-messages",
          f"--merge-base={commit}^", TARGET, commit, check=False)
    if r.returncode != 0:
        files = "\n  ".join(r.stdout.strip().splitlines()[1:]) or r.stderr.strip()
        fail(f"{g('log', '-1', '--format=%h %s', commit).stdout.strip()} conflicts with {TARGET} in:\n  "
             f"{files}\nNothing was copied. Two threads probably disagree: tell the owner. "
             "Then sync (tools/sync.py), resolve, and run again.")
    tree = r.stdout.split()[0]
    if tree == g("rev-parse", f"{TARGET}^{{tree}}").stdout.strip():
        return old  # main already has this change
    fmt = {"GIT_AUTHOR_NAME": "%an", "GIT_AUTHOR_EMAIL": "%ae", "GIT_AUTHOR_DATE": "%aI"}
    env = {k: g("log", "-1", f"--format={v}", commit).stdout.strip() for k, v in fmt.items()}
    msg = g("log", "-1", "--format=%B", commit).stdout  # keeps its Session: trailer
    new = g("commit-tree", tree, "-p", old, "-F", "-", input=msg, env={**os.environ, **env}).stdout.strip()
    g("update-ref", "-m", f"{TOOL}: copy {commit[:9]}", f"refs/heads/{TARGET}", new, old)
    if wt:  # bring that checkout's index and files up to date for just these paths
        for path in paths:
            if g("cat-file", "-e", f"{new}:{path}", check=False).returncode == 0:
                g("checkout", new, "--", path, cwd=wt)
            else:
                g("rm", "-q", "--cached", "--ignore-unmatch", "--", path, cwd=wt)
                (wt / path).unlink(missing_ok=True)
    return new


def doc_pathspecs(cwd) -> list[str]:
    return [d for d in DOCS if (Path(cwd) / d).exists() or g("ls-files", "--", d, cwd=cwd).stdout.strip()]


def publish_docs(subject: str | None):
    specs = doc_pathspecs(REPO)
    changed = g("status", "--porcelain", "-uall", "--", *specs, cwd=REPO).stdout.strip() if specs else ""
    if changed:
        if not subject:
            fail("say what changed with -m")
        g("add", "-A", "--", *specs, cwd=REPO)
        g("commit", "-q", "-F", "-", "--", *specs, cwd=REPO, input=with_trailer(subject))
    if current_branch(REPO) == TARGET:
        print(f"{TOOL}: {'committed the documents on ' + TARGET if changed else 'no document changes'}")
        return
    commits = g("rev-list", "--reverse", "--no-merges", f"{TARGET}..HEAD", cwd=REPO).stdout.split()
    copied = []
    with MainLock():
        for c in commits:
            paths = g("diff-tree", "--no-commit-id", "--name-only", "-r", c).stdout.split()
            if not paths or not all(is_doc(p) for p in paths):
                continue  # code or mixed commits wait for landing
            before = g("rev-parse", TARGET).stdout.strip()
            if copy_to_main(c) != before:
                copied.append(g("log", "-1", "--format=%h %s", c).stdout.strip())
    if not copied:
        print(f"{TOOL}: no document changes to copy to {TARGET}")
    for line in copied:
        print(f"{TOOL}: copied to {TARGET}: {line}")
    if copied:
        after_main_changed()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kind", choices=["docs", *kinds()])
    ap.add_argument("--slug")
    ap.add_argument("--file", help="draft with {ID} where the ID goes")
    ap.add_argument("-m", "--message", help="commit subject; {ID} is filled in")
    a = ap.parse_args()
    if a.kind == "docs":
        return publish_docs(a.message)
    if not (a.slug and a.file):
        fail("an entry needs --slug and --file")
    draft = Path(a.file).read_text(encoding="utf-8")
    if "{ID}" not in draft:
        fail("the draft has no {ID} placeholder")
    add_entry(a.kind, a.slug, lambda eid: draft.replace("{ID}", eid), a.message or f"Add {{ID}}: {a.slug}")


if __name__ == "__main__":
    main()
