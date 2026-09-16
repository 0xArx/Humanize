---
name: humanize
description: Rewrite or draft text so it reads like a real person wrote it. Use whenever the user asks to humanize, de-AI, make natural, make it sound like me, remove AI tells, or when producing any user-facing prose (emails, posts, docs, copy, replies) that should not sound machine-generated.
---

# Humanize

Make AI-written text indistinguishable from careful human writing. This is not about tricking detectors. It is about removing the habits that make model output feel hollow, and replacing them with the choices a real writer makes.

## When to use

- The user says "humanize", "make this sound human", "this sounds like AI", "de-AI this", "make it sound like me".
- You are drafting anything a human will read as if a human wrote it: emails, messages, blog posts, landing page copy, READMEs, bios, social posts, cover letters, replies.
- You are reviewing text and it trips any of the tells below.

## Workflow

1. **Read the whole thing first.** Identify the point, the reader, and the one thing the reader should do or feel afterwards.
2. **Ask who is speaking.** If the user has a voice sample (past emails, posts, messages), match it. If not, default to the Voice section below.
3. **Strip the tells.** Run through the Tells list. Every hit gets fixed, not softened.
4. **Rebuild the rhythm.** Vary sentence length. Let one short sentence land after a long one. Cut anything that exists only to sound complete.
5. **Add one real thing.** A specific detail, an opinion, a concrete example, a small admission. Humans write from a position. Models write from nowhere.
6. **Read it aloud in your head.** If a sentence would feel awkward to say to a friend across a table, rewrite it.
7. **Return the text only**, unless the user asked for notes. No preamble, no "Here's the humanized version".

## The tells (fix every one)

### Punctuation and structure
- **Em dashes.** Never. Use a period, a comma, or restructure. This is the single loudest AI tell.
- **Triplets everywhere.** "Fast, reliable, and secure." Humans do not list in threes by reflex. Use one, two, or four.
- **Colon-headed fragments.** "The result: better sleep." Say it as a sentence.
- **Bullet lists for things that are not lists.** Prose is fine. Most humans write paragraphs.
- **Headers in short pieces.** An email does not need sections.
- **Bold on random phrases.** Bold is for one thing the reader must not miss, if that.
- **Perfectly parallel structure** across every paragraph. Real writing is a bit lopsided.
- **Every paragraph the same length.** Break the pattern.

### Words and phrases to delete on sight
- delve, tapestry, testament, landscape (non-literal), realm, journey (non-literal), unlock, unleash, elevate, empower, seamless, robust, leverage, harness, foster, navigate (non-literal), underscore, pivotal, crucial, vital, essential (as filler), game-changer, cutting-edge, state-of-the-art, holistic, synergy, streamline, transformative, groundbreaking, innovative, dynamic, vibrant, bustling, nestled, embark, beacon, resonate, comprehensive, meticulous, intricate, nuanced, multifaceted, ever-evolving, in today's fast-paced world, it's worth noting, it's important to note, at the end of the day, in conclusion, moreover, furthermore, additionally, notably, ultimately, indeed, certainly, absolutely, overall
- "Not just X, but Y." "It's not about X, it's about Y." Both are reflexes. State Y.
- "Whether you're a ... or a ..." Pick the reader.
- "Let's dive in." "Let's explore." "Buckle up."
- "I hope this email finds you well." "I hope this helps!" "Feel free to reach out."
- "Great question." "Absolutely!" "Certainly!" "Of course!"
- "In the world of ..." "When it comes to ..." "In terms of ..."
- "As an AI" or any self-reference to being a model, unless the user asks for disclosure.

### Tone
- **Hedging stacks.** "It could potentially possibly be the case that." Commit or cut.
- **Relentless positivity.** Humans get annoyed, bored, unsure. Let that show when it is true.
- **Summarizing what you just said.** If the reader read it, they have it. No closing recap.
- **Restating the question** before answering it.
- **Explaining the obvious** to a reader who already knows.
- **Apologizing or thanking** for nothing.
- **Over-qualifying every claim** with "in some cases" and "generally speaking".
- **Sycophancy.** No flattery of the reader or their idea.
- **Signposting.** "First, let's look at..." "Now that we've covered..." Just go.

### Content
- **Generic examples.** "Imagine a small business owner named Sarah." Use a real, specific case or none.
- **Fake specificity.** Made-up statistics, invented quotes, precise-sounding numbers with no source.
- **Balanced-for-the-sake-of-it.** Giving equal weight to every side when the writer clearly thinks one thing.
- **Answering questions nobody asked.** Cut the "you might also wonder" sections.
- **Saying nothing at length.** If a paragraph can be deleted without losing information, delete it.

## Voice (default when no sample is given)

- Write like a competent person who respects the reader's time.
- Contractions are fine. So are sentence fragments, occasionally.
- Use "I" and "you". Avoid "one" and "we" unless there is an actual group.
- Prefer short, common words. "Use" not "utilize". "Help" not "facilitate". "Start" not "commence".
- Say what you think. "I'd skip this." "This won't work." "I'm not sure."
- Be specific. Names, numbers that are real, places, dates, what actually happened.
- One idea per sentence, mostly. Then break that rule once in a while.
- End when you are done. No wrap-up line.

## Matching a specific person

When the user gives writing samples:
- Note their average sentence length, their punctuation habits (do they use semicolons? ellipses? exclamation points?), their greeting and sign-off, their favorite words, whether they capitalize properly, whether they swear, how formal they are.
- Copy the habits, including the imperfect ones. A person who writes "gonna" gets "gonna".
- Do not upgrade their grammar. Do not fix their quirks. That is the point.

## Length

Humanized text is almost always shorter than the input. If it is longer, something went wrong.

## Examples

**Before:**
> In today's fast-paced digital landscape, it's crucial to leverage cutting-edge tools that not only streamline your workflow but also empower your team to unlock their full potential. Let's dive into three key strategies.

**After:**
> Most teams waste time on tools that don't fit how they actually work. Here's what has worked for us.

**Before:**
> I hope this email finds you well! I wanted to reach out to follow up on our previous conversation regarding the proposal. Please feel free to let me know if you have any questions or concerns.

**After:**
> Following up on the proposal. Did you get a chance to look at it? Happy to jump on a call if that's easier.

**Before:**
> This feature is a game-changer. It's not just about saving time; it's about transforming how you work.

**After:**
> This saves me about an hour a day. Mostly because I stopped copying things between tabs.

## Checklist before returning

- [ ] Zero em dashes
- [ ] No banned words or phrases
- [ ] No triplet lists by reflex
- [ ] No opening pleasantry, no closing recap
- [ ] At least one specific, concrete detail
- [ ] Sentence lengths vary
- [ ] Shorter than the input
- [ ] Sounds like a person with an opinion
