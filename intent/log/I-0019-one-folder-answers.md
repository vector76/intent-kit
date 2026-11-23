---
id: I-0019
date: 2026-11-23
captured_from: session 6d25e113-df43-4d10-b870-5932ea9ad280
author: Jamie Kawabata
message_timestamps: [2026-11-23T21:39:30.984Z]
supersedes: []
tags: [layout]
---

<!-- Verbatim human input. Do not edit. Corrections or changes of mind go in a NEW entry. -->
1: yes, configurable with intent-kit as default is good
2: yes project content documents go in there too
3: move the 1.0.0 tag and force push if necessary
4: don't worry about existing projects, there are no existing projects

<!-- Not intent: the agent's question(s) these words answer, quoted from the same session so the words above can be understood. -->

> 1. **The folder's name.** The vision still calls "intent-kit" a placeholder name. I'd make the folder name a setting, with `intent-kit/` as the default, so renaming the kit later doesn't mean moving every project. Is that what you want?

> 2. **Your project's own documents.** The intent log, vision and requirements are the project's content, not kit machinery, and some teams may want them easy to find. You said "everything", so I'd put them in the folder too, unless you'd rather keep `intent/` and `plan/` at the root.

> 3. **Version number.** This changes where every file lives, which by the usual convention makes it 2.0.0. You only just shipped 1.0.0, and you may be the only user so far, so we could instead redo 1.0.0 with the new layout and move the tag again. Which do you prefer?

> 4. **Moving existing projects.** `upgrade` would move an existing project's files into the folder with `git mv`, so history follows them.
