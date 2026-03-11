# Prototype: Bites

## The Problem

Briefings are comprehensive — they synthesize a domain into a multi-section technical document. That's the right format for deep orientation. But not every moment calls for deep orientation. Sometimes the human operator needs a 3-minute understanding of a concept while on a phone, between meetings, or before a quick decision.

## The Idea

A **bite** is a briefing compressed to its minimum viable form. Tailored for mobile consumption. Three minutes or less. Answers the question: "What is this, why does it matter, and what's the one thing I'd get wrong?"

This originated from a simple prompt: *"Give me a 3-minute tutorial on small world networks and knowledge graphs"* — and getting back something genuinely useful at that scale.

## Sizes

- **Bite** (1-bite) — 3 minutes. One concept, one danger, one takeaway. Fits on a phone screen.
- **2-bite** — 5-7 minutes. Adds a worked example or a comparison to a related concept.
- **3-bite** — 10 minutes. Approaches a mini-briefing but still focused on a single thread.

## What Makes a Good Bite

- **Starts with the punchline.** No background preamble. "The grade cache is not the source of truth. Here's why that matters."
- **One mental model.** A bite installs exactly one concept in the reader's head.
- **Names the trap.** Every bite should include the one thing a smart person would get wrong.
- **Links out, doesn't expand.** If you need more, here's the charter / briefing / flow doc. The bite doesn't try to be comprehensive.

## Relationship to Existing Docs

| Format | Depth | Audience | When |
|--------|-------|----------|------|
| Bite | Concept-level | Human operator, mobile | Quick orientation, between meetings |
| Briefing | Domain-level | Human operator or agent | Deep orientation, before planning |
| Charter | API-level | Agent | During implementation |
| Flow doc | Journey-level | Staff, onboarding | Understanding business processes |

## Open Questions

- Should bites live in `docs/briefings/` alongside full briefings, or in their own directory?
- Is there a procedure for generating bites, or are they ad hoc?
- Could bites be auto-generated from charters by an agent? (Extract the tripwire, add one example, done.)
- What's the naming convention? `bite-grade-cache.md`? `bites/grade-cache.md`?
