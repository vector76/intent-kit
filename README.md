# intent-kit (development)

**The kit is the [`kit/`](kit/) folder.** It ships as that folder and nothing else: see
[kit/README.md](kit/README.md) to use it.

Everything outside `kit/` is the record of developing the kit, run by the kit's own
method. It's never copied into a project:

```
intent/log/       the owner's words about the kit, verbatim (I-xxxx)
intent/vision.md  what the kit is meant to be, now
plan/             requirements (R-), decisions (D-), and lessons (L-) from bugs found in the kit
tools/            an installed copy of kit/template/managed/tools/, used to keep this record
record/           this repo's private session record (a separate git repo, ignored)
```

To change the tools, edit `kit/template/managed/`, then run
`python kit/bootstrap.py upgrade . --apply` to install them here, and run the tests
(`python -m unittest discover -s kit/tests -v`).

Some of the kit's sessions ran in other projects' folders. Their transcripts are in
those projects' records, and the intent entries cite them by session id.
