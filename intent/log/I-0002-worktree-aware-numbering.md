---
id: I-0002
date: 2026-11-23
captured_from: session 6d25e113-df43-4d10-b870-5932ea9ad280
author: Jamie Kawabata
message_timestamps: [2026-11-23T06:04:39.198Z]
supersedes: []
tags: [worktrees, numbering]
---

<!-- Verbatim human input. Do not edit. Corrections or changes of mind go in a NEW entry. -->
Something I would add is the parallel threads and the business about work trees and all that was somewhat forced because backplane by default always works in work trees, or well, sort of a hybrid where some things are in work trees and some things are on main. And so in order for the conversations on any session to operate correctly, it has to be aware of that and kind of work around it. And so the intent and some of those things are treated on main as, the subset of things that are on main. And this is peculiar to backplane in that I didn't intend to use work trees, although I think it is something that can potentially be raised in general, because even in Claude Code, for instance, if I say I want to start a work tree, and then while I'm in the work tree, some things happen and there are conversations, it's going to have to be cognizant of that. And so it needs to be a work tree in general. It needs to be work tree aware and treat the writing to the record of intent and so forth as a in the appropriate way, so we don't get collisions and things of intent being added, and especially the numbering gets all messed up. I will mention one option would be to, and I don't know how well I like this, but one option would be to use random identifiers instead of sequence numbers for intent and all these things, because then the collisions are mostly going to not happen. I throw that out there as an option. I don't think, I'm not sure if that's what I prefer, but anyway, either way, we need some awareness of work trees. But it's not something that I was seeking out specifically. I was just sort of forced to deal with it because of how backplane works, I guess, is the point of what I wanted to say.
