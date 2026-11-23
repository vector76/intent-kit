#!/usr/bin/env python3
"""Copy Claude Code session transcripts into the private record repo (record/).

Run automatically by the hooks in .claude/settings.json:
  SessionStart -> remember the session id (for the commit trailer, see .githooks/),
                  then sync + commit anything earlier sessions left uncommitted
  Stop         -> copy the transcript (cheap; keeps the record current after every turn),
                  and commit the record repo every Nth turn (record_commit_every)
  SessionEnd   -> copy the transcript and commit the record repo

Run by hand to sweep up every session of this project, worktree sessions included
(e.g. if a session ended without firing SessionEnd, or when adopting an existing project):
  python tools/capture_session.py --all [--commit]

The record is always its own git repository, ignored by this one. It holds raw
transcripts: system prompts, file contents, tool output and personal details. If
record/ is not safely ignored, nothing is copied and the session is warned.

Managed by intent-kit.
"""
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import (CFG, CURRENT, RECORD, SESSIONS, TURNS, find_transcript, git,  # noqa: E402
                    record_problem, remember_transcript_dir, transcript_dirs)


def session_date(transcript: Path) -> str:
    with transcript.open(encoding="utf-8") as f:
        for line in f:
            m = re.search(r'"timestamp":\s*"(\d{4}-\d{2}-\d{2})', line)
            if m:
                return m.group(1)
    return "undated"


def copy_session(transcript: Path) -> Path | None:
    if not transcript.is_file():
        return None
    sid = transcript.stem
    SESSIONS.mkdir(parents=True, exist_ok=True)
    existing = list(SESSIONS.glob(f"*_{sid}.jsonl"))
    dest = existing[0] if existing else SESSIONS / f"{session_date(transcript)}_{sid}.jsonl"
    src = transcript.stat()
    if dest.exists():
        d = dest.stat()
        if d.st_size == src.st_size and int(d.st_mtime) == int(src.st_mtime):
            return dest  # unchanged since last copy (copy2 keeps mtime)
    shutil.copy2(transcript, dest)
    side = transcript.with_suffix("")  # <id>/ folder: subagent transcripts, tool results
    if side.is_dir():
        shutil.copytree(side, dest.with_suffix(""), dirs_exist_ok=True)
    return dest


def commit_record(message: str):
    if not (RECORD / ".git").exists():
        return
    git("add", "-A", cwd=RECORD)
    if git("diff", "--cached", "--quiet", cwd=RECORD).returncode != 0:
        git("commit", "-q", "-m", message, cwd=RECORD)


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
            sys.exit(f"capture_session: FAILED: {problem}; nothing copied. Run python tools/kit.py check.")
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
                  "Tell the owner and run `python tools/kit.py check`.")
            return
        if transcript.is_file():
            remember_transcript_dir(transcript)
        # SessionEnd doesn't always fire (apps get closed), so commit whatever earlier
        # sessions left behind each time a new one starts. Otherwise no stdout here.
        sync_all()
        commit_record(f"sync at start of session {sid}")
        return
    if problem:
        print(f"capture_session: not recording: {problem}", file=sys.stderr)
        return
    copy_session(transcript)
    if event == "SessionEnd":
        commit_record(f"session {sid}")
    elif event == "Stop" and sid:
        turn = count_turn(sid)
        every = max(1, int(CFG.get("record_commit_every") or 10))
        if turn % every == 0:
            commit_record(f"session {sid}: turn {turn}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:  # never block the session over record-keeping
        print(f"capture_session: {e}", file=sys.stderr)
