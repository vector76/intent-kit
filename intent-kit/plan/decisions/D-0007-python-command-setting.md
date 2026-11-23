---
id: D-0007
date: 2026-11-23
status: active
from: [I-0008]
---
# The Python command is a project setting, found at bootstrap and checked after

**Decision:** `intent-kit.json` has a `"python"` setting: the command the hooks and the
generated rules use to run the tools (`python3`, `python`, `py -3` or a full path). The
bootstrap takes `--python`, or else uses the first of the usual commands that runs
Python 3.10 or later. On Windows `python3` is tried last, because it's often the Store's
placeholder. If none works, the bootstrap stops before writing anything and says the
owner needs to install Python. `kit.py check` reports a problem if the command doesn't
run or is too old. `kit.py render` keeps the hook commands in `.claude/settings.json` in
step with the setting. Projects from older kits get `"python": "python"` on upgrade,
since that's what their hooks already ran.

**Why:** The owner asked that onboarding check Python is available (I-0008). A hook
whose command doesn't run records nothing, and it fails without saying so: the session
carries on unrecorded. Fixing `python` in the hooks would break on a stock macOS, which
has only `python3`.

**Alternatives considered:** a hard-coded `python3` (fails on many Windows machines); a
check in the onboarding text only, with no setting (nothing to fix the hooks with
afterwards).

**Revisit if:** hooks need to run somewhere without a usable Python on PATH, such as a
sandbox or container.
