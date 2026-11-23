# The method

A project run this way keeps two things that most projects lose: **what the owner
actually wants**, in their own words, and **how every output came to be**. The rest of
the structure exists to serve those two.

## The loop: intent, projection, work, reconciliation

The usual picture of making something goes intent → specification → implementation.
The specification can take many forms: a requirements document, a prompt, user
documentation, a list of use cases. Then the implementation is checked against the
specification.

That picture is missing two things.

First, **the intent is rarely recorded at all.** It lives in the owner's head, and what
gets written down is already a rendering of it: a specification, shaped by whoever
wrote it. When the owner forgets, or changes their mind, there is nothing to go back to.

Second, **the real check is against the intent, not the specification.** Seeing the
thing built often teaches the owner something: "yes, that's what I asked for, but now
that I see it, it's not what I want." That isn't a failed test. It is new intent, and it
should flow back. A prototype that wobbles, a calculation that rules out a whole region,
a part that won't print: reality corrects the intent, and the intent changes.

So the method is a loop. The owner's intent is captured as it is spoken. It is
*projected* into a current vision, requirements, decisions and experiments. The work is
done. What the work teaches comes back as new intent, and the projections are redrawn.
It is closer to agile than to waterfall, but with a memory.

## Intent is messy, and is kept that way

Intent is fluid, half-formed, sometimes contradictory, often sloppy. Asides count ("that's
interesting, but not now"). Carving intent down to a consistent subset leaves out most of
what's interesting, so the log doesn't try.

Intent is therefore recorded **verbatim**: the owner's own words, extracted from the
session transcript by a tool and never retyped or paraphrased. A paraphrase is already a
projection, and it quietly loses whatever the paraphraser didn't think mattered. The log
is **append-only**. A change of mind is a new entry that says what it supersedes; the old
entry stays, so it's always clear what was said, when, and what replaced it.

Intent about how the project is run counts too. Choosing where the record lives, or how
work lands, is the owner's intent like anything else, and it goes in the same log. A
reader who wants only one kind can ask for a rendering that picks it out. The log
doesn't have to be split for that.

## Projections: the current view

The vision, the requirements and the roadmap are **projections** of the intent: a shadow
of the whole log, cast from where things stand today. When the intent changes, the
projection is redrawn, not annotated.

**A current-view document carries no history.** It says what is true now. There are no
"superseded" sections, changelogs or strike-throughs. Kept history in a living document
grows until it covers more ground than the current view, and the reader can no longer
tell what holds. Git already keeps every past version for anyone who wants to see how
things changed. The one exception is a point that would otherwise look wrong: keep a
short reason there ("because the tipping test failed at 30°"), not the story.

Projections are honest about firmness. A requirement says whether it is hard, a target,
an expectation, or only an example the owner gave to make an idea concrete. **An example
is an example**, not a commitment, and it isn't promoted to one without the owner saying
so.

## Contradictions are surfaced, not resolved

When two intent entries conflict, or a request conflicts with the vision, the agent
doesn't quietly pick a side. The contradiction goes under *Open questions and tensions*
in the vision and is put to the people whose intent it is. Contradiction in intent is
normal, so it is kept in plain view, where it can be decided on purpose.

## According to whom

More than one person may state intent for a project. Most of it agrees or is about
different things, but every entry still records whose words it is. A contradiction can
surface long after the words were written, and by then nobody remembers who said what.

Authorship is there so people know whom to talk to, not as proof. Each session belongs to
one person, who is named once in each clone. The intent captured from a session is that
person's. The method never records words as someone else's. When someone passes on
another person's wishes, the entry records both: who said it, and whose wishes they say
it is. It counts as the speaker's view of what the other person wants until that person
says it themselves. Agreeing with an entry is a new entry, by the person who agrees.

The projections are written as the consensus and name no one. Where people want
different things, the vision's open questions say who holds each view, so they can talk
it through. The agent surfaces the difference and doesn't decide between people.

## What's known is kept apart from what's wanted

Facts about the world (science, prior work, prices, how a part behaves) are not intent.
Where a project needs them, they go in their own layer, with sources a reader can check
and anything unverified marked as such. Intent is the owner's; research is the world's.
Blending them lets a wish pass for a fact, or a fact pass for a decision.

## Provenance: every output traces back

Every artifact should be traceable to the session that made it, and through that session
to the intent in force at the time. This is what makes an after-the-fact audit possible:
why is this the way it is? Was this mistake made before, and where did it come from?

The chain is:
- Every commit carries a `Session:` trailer naming the AI session that made it.
- Every session's raw transcript is kept in the record.
- Every intent entry names its author and the session and message it was extracted from.
- Every decision says who agreed to it, and every lesson who found the problem.
- Every requirement, decision and experiment cites the IDs it rests on.

## The record is private, and always separate

Raw transcripts are candid. They hold system prompts, file contents, tool output and
personal details. So they live in a **separate git repository** next to the project and
ignored by it, never inside it. That holds even when the project itself is published.
Mixing the two invites the easy mistake of publishing the record with the work, and the
tools refuse to record anything if the separation is broken. The record can still have
its own private remote, so several people can push and pull it, and session files are
named by their unique ids, so records merge without conflict.

## Lessons make mistakes findable

When a mistake is found, it gets a short postmortem: what happened, in which session and
commit, its root cause (bad intent, bad projection, bad execution, bad source, or a
missing check), and a concrete way to avoid it. If the fix is a rule, the rule goes into
the agents' working instructions. Agents read the lessons before related work, so the
same mistake is caught the second time.

## Parallel work: one line of numbers, one current view

Work often happens in parallel: in git worktrees (which some tools use by default), on
branches, or in several sessions at once. Two things go wrong if nothing is done about
it. Numbered entries collide, when two threads each take "the next number". And intent
gets stranded on a branch that never lands.

The answer is that **the record of intent and the plan don't wait for landing**:
- A new numbered entry (intent, decision, lesson, and so on) is committed to the main
  branch the moment it's created, wherever the session is running. Main hands out the
  numbers, so they never collide, and intent captured in a thread that's later abandoned
  still reaches the log.
- The current-view documents go to main as soon as they're edited, so every thread works
  from the current vision. If two threads change the same part differently, the tool
  stops and reports it rather than merging. That usually means the threads disagree,
  which is a contradiction for the owner to see.
- Everything else (code, designs, experiment work) lands normally, by whatever policy the
  project chose.

## What the method leaves to each project

Some choices belong to the project, and the owner makes them when it's set up:
- whether the work is confidential or meant to be published
- which further layers it needs (research, concepts, experiments, artifact folders)
- how work lands on main: linear history or merges
- stances some projects want, such as keeping the search space wide open, or judging
  plausibility by what would enable a path rather than by consensus that it failed before

The answers go into the project's configuration, which cites the owner's words in the
record. They don't open the project's intent log: setting the method up isn't intent
about the project, and the log starts with what the project is for. When the owner later
changes one of these choices, that is intent like any other, captured in the log and
cited by the configuration.

A project gets the method, not anyone's history. Its log, decisions and lessons start
empty and fill with its own.
