#!/usr/bin/env python3
"""Pull the human-typed messages out of a Claude Code session transcript (JSONL).

Used to create intent-log entries *verbatim*: never retype or paraphrase the
human's words; extract them.

  List messages (* = its text is already in an intent entry on main;
                 c = cited by intent-kit/config.json as an onboarding answer):
    python intent-kit/tools/extract_human_messages.py <session-id or .jsonl> --list

  Write an intent entry from one or more messages:
    python intent-kit/tools/extract_human_messages.py <session-id> \
        --slug short-name --msg 4 [5 ...] [--supersedes I-0001] [--tags cost,assembly]
        [--on-behalf-of NAME] [--question "<the agent's question, quoted exactly>" ...]

Every entry names its author: the person whose session it is. A session is one person's,
so the author comes from the record's note of the session (written by the hooks), or, for
a transcript on this machine, from the name set up in this clone (`kit.py whoami`). Only
when neither is known does --author NAME say whose it is. Words are never recorded as
someone else's: when the speaker relays another person's wishes ("Alice wants X"),
--on-behalf-of Alice records that claim, and the entry stays the speaker's.

When a message answers the agent's questions and can't be understood without them
("1: yes, 2: no"), --question (or --question-file, for long or awkward text) adds the
questions that are needed, as a block marked as the agent's words and not intent. Each
must be quoted exactly from the agent's text earlier in the same session; the tool checks.
It's a judgment call, not a rule: when the words make sense on their own, add no question,
and quote only the questions the words depend on.

The entry gets the next free I- number on main and is committed straight to main
(intent-kit/tools/to_main.py), wherever this runs, so two sessions or worktrees capturing at
once never pick the same number. Then update intent/vision.md and run
`python intent-kit/tools/to_main.py docs -m "..."`.

A bare session id is looked up in Claude's transcript folders for this project
first (the live transcript, worktrees included), then in the private record.

Managed by intent-kit.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kitlib import (CFG, CONFIG_NAME, SESSIONS, find_transcript, is_local_transcript,  # noqa: E402
                    kinds, main_file_text, main_tree_files, my_name, session_author, yaml_str, TOOLS_REL)

LOG = kinds()["intent"][0]
# Text that arrives as a "user" record but isn't the human's: command wrappers and system
# injections start with "<"; projects can add more (Backplane's thread reports, say).
NOT_HUMAN = tuple(["<", *CFG.get("not_human_prefixes", [])])
# Records that are typed "user" but were written by Claude Code, not typed by the human.
SKIP_FLAGS = ("isMeta", "isSidechain", "isCompactSummary", "isVisibleInTranscriptOnly")


def resolve(path_or_id: str) -> Path:
    p = Path(path_or_id)
    if p.is_file():
        return p
    live = find_transcript(path_or_id)  # live first: the record copy can lag a running session
    if live:
        return live
    for cand in SESSIONS.glob(f"*{path_or_id}*.jsonl"):
        return cand
    sys.exit(f"transcript not found: {path_or_id}")


def human_text(s) -> bool:
    return isinstance(s, str) and bool(s.strip()) and not s.lstrip().startswith(NOT_HUMAN)


def human_messages(path: Path):
    """Return [(timestamp, session_id, text)] for messages the human actually typed,
    in transcript order.

    Two kinds of record carry them:
      - type "user": an ordinary turn, where the human typed and waited.
      - type "queue-operation", operation "enqueue": a message sent while the agent was
        working. When it is absorbed mid-turn it NEVER appears as a "user" record, so
        reading only those silently loses that intent.
    A queued message that is delivered as its own turn appears in both, so the queued
    copy is dropped when an ordinary record holds the same text. Compaction summaries,
    meta records and subagent prompts are typed "user" too, and are skipped.
    """
    typed, queued = [], []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            kind = d.get("type")
            if kind == "queue-operation":
                # "remove" repeats the text of the same message; take it once, at enqueue
                if d.get("operation") == "enqueue" and human_text(d.get("content")):
                    queued.append((d.get("timestamp", ""), d.get("sessionId", ""), d["content"]))
                continue
            if kind != "user" or any(d.get(flag) for flag in SKIP_FLAGS):
                continue
            content = (d.get("message") or {}).get("content")
            if isinstance(content, list):  # tool results / mixed blocks: keep the human's text only
                parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                content = "\n".join(p for p in parts if human_text(p))
            if not human_text(content):
                continue
            typed.append((d.get("timestamp", ""), d.get("sessionId", ""), content))

    seen = {t.strip() for _, _, t in typed}
    msgs = typed + [q for q in queued if q[2].strip() not in seen]
    msgs.sort(key=lambda m: m[0])
    return msgs


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


SEPARATOR = "\n\n---\n\n"  # between messages in one entry (see render below)
# Starts the optional block of the agent's questions, after the human's words.
CONTEXT_MARK = "<!-- Not intent: "
CONTEXT_NOTE = (CONTEXT_MARK + "the agent's question(s) these words answer, quoted from the same session so "
                "the words above can be understood. -->")


def agent_messages(path: Path):
    """Return [(timestamp, text)] for the agent's own text in the main conversation (not subagents')."""
    out = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if d.get("type") != "assistant" or d.get("isSidechain"):
                continue
            content = (d.get("message") or {}).get("content")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                text = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            else:
                continue
            if text.strip():
                out.append((d.get("timestamp", ""), text))
    return out


def quoted_question(q: str, said: list[tuple[str, str]], before: str) -> bool:
    """True if q is the agent's own words (whitespace aside) from before `before`."""
    n = _norm(q)
    return bool(n) and any(n in _norm(text) for ts, text in said if ts < before)


def entry_messages(text: str) -> list[str]:
    """The verbatim messages in one intent entry: the body after the front matter and the
    'Verbatim human input' comment, split where render() joined them."""
    body = text
    if body.startswith("---"):
        parts = body.split("\n---\n", 1)  # end of front matter
        body = parts[1] if len(parts) == 2 else body
    body = re.sub(r"^\s*<!--.*?-->\s*", "", body, count=1, flags=re.S)
    body = body.split(CONTEXT_MARK, 1)[0]  # the agent's questions, if any, aren't the human's words
    return [m for m in body.strip().split(SEPARATOR) if m.strip()]


def captured_messages() -> set[str]:
    """Every message already in an intent entry on main, whitespace-normalized. Matching is by
    whole message: a short message ("yes") isn't counted as captured just because those
    words appear inside a longer one. A message that itself contains a line of `---` may fail
    to match; it then shows as unmarked, which errs on the side of checking it."""
    out = set()
    for p in main_tree_files(LOG):
        if p.endswith(".md"):
            out.update(_norm(m) for m in entry_messages(main_file_text(p)))
    return out


def cited_messages() -> set[tuple[str, str]]:
    """(session, timestamp) of messages the config on main cites as sources (onboarding answers)."""
    try:
        sources = json.loads(main_file_text(CONFIG_NAME) or "{}").get("sources", {})
    except json.JSONDecodeError:
        return set()
    return {(r.get("session", ""), r.get("message", "")) for refs in sources.values()
            for r in refs if isinstance(r, dict)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--slug", help="short name; writes the entry")
    ap.add_argument("--msg", type=int, nargs="+", help="message numbers from --list")
    ap.add_argument("--supersedes", default="", help="comma-separated intent ids")
    ap.add_argument("--tags", default="")
    ap.add_argument("--on-behalf-of", default="", metavar="NAME",
                    help="the speaker is relaying NAME's wishes; the entry stays the speaker's")
    ap.add_argument("--author", default="", help="only when the session's author isn't known")
    ap.add_argument("--question", action="append", default=[],
                    help="an agent question the words can't be understood without, quoted exactly")
    ap.add_argument("--question-file", action="append", default=[], help="the same, read from a file")
    a = ap.parse_args()

    path = resolve(a.transcript)
    msgs = human_messages(path)
    sid = msgs[0][1] if msgs else path.stem.split("_")[-1]
    known = session_author(sid) or (my_name() if is_local_transcript(path) else "")
    if a.list or not a.slug:
        done, cited = captured_messages(), cited_messages()
        n_done = n_cited = 0
        for i, (ts, sid, text) in enumerate(msgs, 1):
            if _norm(text) in done:
                mark = "*"
                n_done += 1
            elif (sid, ts) in cited:
                mark = "c"
                n_cited += 1
            else:
                mark = " "
            print(f"{i:3d}{mark} {ts[:19]}  {text[:90].replace(chr(10), ' ')}")
        print(f"\nSession author: {known or 'unknown (see --author)'}")
        print(f"\n{n_done} of {len(msgs)} message(s) are in an intent entry on main (*)"
              + (f", {n_cited} are cited by {CONFIG_NAME} as setup answers (c)" if n_cited else "")
              + ". Not every message is intent; check each unmarked one.")
        return

    if not a.msg:
        sys.exit("--slug needs --msg")
    if any(n < 1 or n > len(msgs) for n in a.msg):
        sys.exit(f"--msg numbers run from 1 to {len(msgs)}; see --list")
    chosen = [msgs[n - 1] for n in a.msg]
    author = a.author.strip()
    if author and known and author != known:
        sys.exit(f"this session is {known}'s; its words can't be recorded as {author}'s. If {known} is "
                 f"passing on {author}'s wishes, use --on-behalf-of {author!r}")
    author = author or known
    if not author:
        sys.exit("whose session is this? Nothing records it" + (
            ": this clone hasn't been told who works in it. Ask them what to call them, then run "
            f"python {TOOLS_REL}/kit.py whoami --set \"<name>\"" if is_local_transcript(path) else
            ". Ask the person whose session it was, then pass --author \"<name>\""))
    behalf = a.on_behalf_of.strip()
    if behalf == author:
        behalf = ""
    questions = [q.strip() for q in a.question + [Path(f).read_text(encoding="utf-8") for f in a.question_file]]
    if questions:
        said, last = agent_messages(path), max(ts for ts, _, _ in chosen)
        bad = [q for q in questions if not quoted_question(q, said, last)]
        if bad:
            sys.exit("not the agent's words from earlier in this session (quote the question exactly): "
                     + "; ".join(repr(q[:60]) for q in bad))

    def lst(s):
        return "[" + ", ".join(x.strip() for x in s.split(",") if x.strip()) + "]"

    def render(eid):
        front = [
            "---",
            f"id: {eid}",
            f"date: {chosen[0][0][:10]}",
            f"captured_from: session {chosen[0][1]}",
            f"author: {yaml_str(author)}",
            *([f"on_behalf_of: {yaml_str(behalf)}"] if behalf else []),
            f"message_timestamps: [{', '.join(ts for ts, _, _ in chosen)}]",
            f"supersedes: {lst(a.supersedes)}",
            f"tags: {lst(a.tags)}",
            "---",
            "",
            "<!-- Verbatim human input. Do not edit. Corrections or changes of mind go in a NEW entry. -->",
            "",
        ]
        body = SEPARATOR.join(text.strip() for _, _, text in chosen)
        if questions:
            quotes = "\n\n".join("\n".join(("> " + ln).rstrip() for ln in q.splitlines()) for q in questions)
            body += "\n\n" + CONTEXT_NOTE + "\n\n" + quotes
        return "\n".join(front) + body + "\n"

    from to_main import add_entry  # imported late: it syncs the branch afterwards
    add_entry("intent", a.slug, render, f"Capture {{ID}}: {a.slug}")


if __name__ == "__main__":
    main()
