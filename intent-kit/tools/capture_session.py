#!/usr/bin/env python3
"""Copy Claude Code session transcripts into the private record repo (record/).

Run automatically by the hooks in .claude/settings.json:
  SessionStart -> remember the session id (for the commit trailer, see githooks/),
                  then sync + commit anything earlier sessions left uncommitted
  Stop         -> copy the transcript (cheap; keeps the record current after every turn),
                  and commit the record repo every Nth turn (record_commit_every)
  SessionEnd   -> copy the transcript and commit the record repo

Run by hand to sweep up every session of this project, worktree sessions included
(e.g. if a session ended without firing SessionEnd, or when adopting an existing project):
  python intent-kit/tools/capture_session.py --all [--commit]

Each copied session gets a note of whose it is (<date>_<id>.author): the person this
clone is set up for (`kit.py whoami`). A session is one person's, so the note is written
once and never changed. If no one is set up yet, the session start asks the agent to ask.

The record is always its own git repository, ignored by this one. It holds raw
transcripts: system prompts, file contents, tool output and personal details. If
record/ is not safely ignored, nothing is copied and the session is warned.

Managed by intent-kit.
"""
import json
import os
import random
import re
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import record_secrets  # noqa: E402
from kitlib import (CFG, CURRENT, RECORD, SESSIONS, TOOLS_REL, TURNS, author_file, find_transcript, git,  # noqa: E402
                    my_name, record_problem, remember_transcript_dir, suggested_name, transcript_dirs)


def session_date(transcript: Path) -> str:
    with transcript.open(encoding="utf-8") as f:
        for line in f:
            m = re.search(r'"timestamp":\s*"(\d{4}-\d{2}-\d{2})', line)
            if m:
                return m.group(1)
    return "undated"


def copy_file(src: Path, dest: Path, targets: set[str]):
    """Copy, redacting any secret the owner has had scrubbed; keep src's times either way."""
    if targets:
        try:
            text = src.read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            text = None
        if text is not None:
            dest.write_bytes(record_secrets.redact(text, targets)[0].encode("utf-8"))
            s = src.stat()
            os.utime(dest, ns=(s.st_atime_ns, s.st_mtime_ns))
            return
    shutil.copy2(src, dest)


def note_author(dest: Path):
    """Write whose session this is, once. Transcripts copied from this machine's Claude folders
    are the sessions of the person this clone is set up for."""
    note = author_file(dest)
    name = my_name()
    if name and not note.exists():
        note.write_text(name + "\n", encoding="utf-8", newline="\n")


def copy_session(transcript: Path) -> Path | None:
    if not transcript.is_file():
        return None
    sid = transcript.stem
    SESSIONS.mkdir(parents=True, exist_ok=True)
    existing = list(SESSIONS.glob(f"*_{sid}.jsonl"))
    dest = existing[0] if existing else SESSIONS / f"{session_date(transcript)}_{sid}.jsonl"
    note_author(dest)
    targets = record_secrets.hashes(record_secrets.REDACTED)
    src = transcript.stat()
    if dest.exists():
        d = dest.stat()
        if d.st_mtime_ns == src.st_mtime_ns and (targets or d.st_size == src.st_size):
            return dest  # unchanged since last copy (the copy keeps the source's times)
    copy_file(transcript, dest, targets)
    side = transcript.with_suffix("")  # <id>/ folder: subagent transcripts, tool results
    if side.is_dir():
        for f in side.rglob("*"):
            if f.is_file():
                out = dest.with_suffix("") / f.relative_to(side)
                if out.is_file() and out.stat().st_mtime_ns == f.stat().st_mtime_ns:
                    continue
                out.parent.mkdir(parents=True, exist_ok=True)
                copy_file(f, out, targets)
    return dest


def commit_record(message: str, paths: list[Path] | None = None, tries: int = 20) -> bool:
    """Commit the record: everything, or only these paths (one session's files), so sessions
    sharing a checkout commit independently. Another commit in progress holds git's index lock
    for a moment; wait and retry rather than drop this one."""
    if not (RECORD / ".git").exists():
        return False
    spec = [p.relative_to(RECORD).as_posix() for p in paths if p.exists()] if paths is not None else ["."]
    if not spec:
        return False
    for _ in range(tries):
        r = git("add", "-A", "--", *spec, cwd=RECORD)
        if r.returncode == 0:
            if git("diff", "--cached", "--quiet", "--", *spec, cwd=RECORD).returncode == 0:
                return False
            r = git("commit", "-q", "-m", message, *(["--", *spec] if paths is not None else []), cwd=RECORD)
            if r.returncode == 0:
                return True
        if "index.lock" not in (r.stderr or ""):
            print(f"capture_session: record commit failed: {(r.stderr or '').strip()}", file=sys.stderr)
            return False
        time.sleep(0.2 + random.random() * 0.3)
    print("capture_session: the record stayed busy; the next commit will include this", file=sys.stderr)
    return False


def count_turn(sid: str) -> int:
    """Add one to this session's turn count and return it."""
    TURNS.mkdir(parents=True, exist_ok=True)
    f = TURNS / sid
    try:
        n = int(f.read_text(encoding="utf-8").strip()) + 1
    except (OSError, ValueError):
        n = 1
    f.write_text(f"{n}\n", encoding="utf-8")
    return n


def sync_all() -> int:
    n = 0
    for d in transcript_dirs():
        for t in sorted(d.glob("*.jsonl")):
            if copy_session(t):
                n += 1
    return n


def main():
    problem = record_problem()
    if "--all" in sys.argv:
        if problem:
            sys.exit(f"capture_session: FAILED: {problem}; nothing copied. Run python {TOOLS_REL}/kit.py check.")
        n = sync_all()
        print(f"capture_session: synced {n} session(s) into {SESSIONS}")
        if "--commit" in sys.argv:
            commit_record(f"sync {n} session(s)")
        return

    try:
        hook = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    event = hook.get("hook_event_name", "")
    sid = hook.get("session_id", "")
    transcript = Path(hook.get("transcript_path") or "")
    if not transcript.is_file():
        transcript = find_transcript(sid) or transcript

    if event == "SessionStart" and sid:
        CURRENT.parent.mkdir(parents=True, exist_ok=True)
        CURRENT.write_text(sid + "\n", encoding="utf-8")
        if problem:
            # A SessionStart hook's stdout is added to the agent's context: say it there.
            print(f"intent-kit WARNING: this session is NOT being recorded: {problem}. "
                  f"Tell the owner and run `python {TOOLS_REL}/kit.py check`.")
            return
        if transcript.is_file():
            remember_transcript_dir(transcript)
        if not my_name():
            guess = suggested_name()
            print("intent-kit: this clone doesn't know who is working in it, so this session and the intent "
                  "captured from it can't be attributed. Before other work, ask the person \"What shall I call "
                  "you?\"" + (f", suggesting \"{guess}\"" if guess else "") + ", then run `python "
                  f"{TOOLS_REL}/kit.py whoami --set \"<name>\"`. Use the name they give, "
                  "not a guess.")
        # SessionEnd doesn't always fire (apps get closed), so commit whatever earlier
        # sessions left behind each time a new one starts. Otherwise no stdout here.
        sync_all()
        commit_record(f"sync at start of session {sid}")
        record_secrets.scan()
        note = record_secrets.reminder()
        if note:
            print(note)  # into the agent's context, to pass on to the owner
        return
    if problem:
        print(f"capture_session: not recording: {problem}", file=sys.stderr)
        return
    dest = copy_session(transcript)
    mine = [dest, dest.with_suffix(""), author_file(dest)] if dest else None  # this session's files only
    if event == "SessionEnd":
        # SessionEnd hooks get little time, so no scan here: the last Stop scanned already
        commit_record(f"session {sid}", mine)
    elif event == "Stop" and sid:
        turn = count_turn(sid)
        every = max(1, int(CFG.get("record_commit_every") or 10))
        if turn % every == 0:
            commit_record(f"session {sid}: turn {turn}", mine)
        new = record_secrets.scan()
        if new:  # a Stop hook's systemMessage is shown to the owner
            print(json.dumps({"systemMessage": (
                f"intent-kit: {len(new)} possible secret(s) just reached the private record. "
                f"`python {TOOLS_REL}/record_secrets.py` lists them, masked; ask the agent to scrub or ignore them.")}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never block the session over record-keeping
        print(f"capture_session: {e}", file=sys.stderr)
