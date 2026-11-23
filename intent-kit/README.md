# intent-kit: intent and record

**Confidential. Never publish this repository.**

Everything the intent-kit method keeps for this project, in one folder so it doesn't mix with the project's own files.

```
intent/log/       people's words, verbatim, append-only, each naming its author (I-xxxx)
intent/vision.md  current view, synthesized from the log
plan/             requirements (R-), decisions (D-), lessons learned (L-)
tools/            record-keeping scripts
githooks/         the hook that adds a Session: trailer to each commit
config.json       how this project is run, citing what set each choice
METHOD-RULES.md   working rules for agents, generated from config.json
record/           raw session transcripts: a separate private repository, ignored
```

People's intent is recorded verbatim, projected into a current vision and plan, and corrected by what the work teaches. Commits reference the session that made them by a `Session:` trailer. See [METHOD.md](METHOD.md).
