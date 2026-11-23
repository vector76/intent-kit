# Intent

- `log/` holds people's own words, verbatim and dated, each naming its author.
  **Append-only:** entries are never edited. A change of mind is a new entry with `supersedes: [I-xxxx]` in its
  front matter. When reading the log, a superseded entry is history, not the current view.
- `vision.md` is the current view, synthesized from the log. It holds no history.

Intent is allowed to be messy: contradictory, half-formed, sloppy, changing. That's the
point of keeping it verbatim. Asides ("that's interesting, but not now") count as intent
too and get captured. So does intent about how the project is run and recorded: it goes
in the same log, unmarked, and the vision and `CLAUDE.md` each take what they need.

## Adding an entry

Extract it from the session transcript; never retype or paraphrase it:

```
python intent-kit/tools/extract_human_messages.py <session-id> --list
python intent-kit/tools/extract_human_messages.py <session-id> --slug short-name --msg 4 5 --tags cost-model
```

`--list` marks with `*` each message whose text is already in an entry on main. The
tool takes the next free I- number on main and commits the entry there straight away,
from whatever branch or worktree you are in. One entry can span several messages from
the same conversation. Not every message is intent ("go ahead", "looks good"), so
capture the ones that state, refine or change what is wanted.

## Answers to the agent's questions

Some messages only make sense next to the question they answer ("1: yes, 2: no"). For
those, add the questions the words depend on:

```
python intent-kit/tools/extract_human_messages.py <session-id> --slug short-name --msg 9 \
    --question "Keep a separate attribution file, or add an author: line to each entry?"
```

The tool checks that each question is quoted exactly from the agent's earlier words in
that session. It adds them after the human's words, as a block marked as not intent.
This is a judgment call, not a rule. When a message makes sense on its own, add no
question. When most of it does and one part doesn't, quote only the question that part
needs. Long or awkward text can go in a file (`--question-file`).

## According to whom

Each entry's `author:` is the person who typed the words, taken from the session they
came from: a session is one person's. Each clone is told once who works in it
(`python intent-kit/tools/kit.py whoami --set "<name>"`). That's for knowing whom to talk to
when intent conflicts, not proof of identity.

- **Words are never recorded as someone else's.** When someone passes on another
  person's wishes ("Alice wants X"), capture it with `--on-behalf-of Alice`. The entry
  stays the speaker's, and it counts as the speaker's view of what Alice wants until
  Alice says it in their own session.
- **Agreeing is a new entry**, by the person who agrees.
- **The vision and requirements are written as the consensus** and name no one. Where
  people's intent differs, the vision's open questions say who holds each view.

If something is too candid even for this repo, put it in the private record
(`intent-kit/record/notes/`) and give it an entry with a one-line neutral summary and the record
path (`python intent-kit/tools/to_main.py intent --slug ... --file draft.md`), so the trace
stays intact.

After adding entries, update `vision.md` (and `intent-kit/plan/requirements.md`, if affected) so it
shows the new current view, and publish it with `python intent-kit/tools/to_main.py docs -m "..."`.
