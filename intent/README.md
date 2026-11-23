# Intent

- `log/` holds the owner's own words, verbatim and dated. **Append-only:** entries are
  never edited. A change of mind is a new entry with `supersedes: [I-xxxx]` in its
  front matter. When reading the log, a superseded entry is history, not the current view.
- `vision.md` is the current view, synthesized from the log. It holds no history.

Intent is allowed to be messy: contradictory, half-formed, sloppy, changing. That's the
point of keeping it verbatim. Asides ("that's interesting, but not now") count as intent
too and get captured. So does intent about how the project is run and recorded: it goes
in the same log, unmarked, and the vision and `CLAUDE.md` each take what they need.

## Adding an entry

Extract it from the session transcript; never retype or paraphrase it:

```
python tools/extract_human_messages.py <session-id> --list
python tools/extract_human_messages.py <session-id> --slug short-name --msg 4 5 --tags cost-model
```

`--list` marks with `*` each message whose text is already in an entry on main. The
tool takes the next free I- number on main and commits the entry there straight away,
from whatever branch or worktree you are in. One entry can span several messages from
the same conversation. Not every message is intent ("go ahead", "looks good"), so
capture the ones that state, refine or change what is wanted.

If something is too candid even for this repo, put it in the private record
(`record/notes/`) and give it an entry with a one-line neutral summary and the record
path (`python tools/to_main.py intent --slug ... --file draft.md`), so the trace
stays intact.

After adding entries, update `vision.md` (and `plan/requirements.md`, if affected) so it
shows the new current view, and publish it with `python tools/to_main.py docs -m "..."`.
