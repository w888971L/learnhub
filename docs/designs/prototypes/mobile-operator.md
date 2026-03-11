# Prototype: Mobile Operator Console

## The Problem

The human operator's role in constitutional architecture is increasingly meta-level: reviewing plans, making decisions, sensing drift, directing agents. Very little of this requires reading or writing code. Yet current tooling assumes the operator is sitting at a desktop with a terminal, IDE, and full-screen browser.

This is an artificial constraint. Most of what the operator does — approve a plan, read a dev log entry, ask an agent to investigate something, review a bite-sized briefing — fits naturally into a text conversation on a phone.

## The Idea

A **mobile operator console** that lets the human operator manage the full agent team from a phone. The communication style is conversational text — the same modality the operator already uses with agents, but untethered from the desktop.

## What the Operator Actually Does

Looking at the workflow that emerged in this project, the operator's actions are:

- **Read** — dev log entries, plan summaries, agent reviews, bites
- **Decide** — approve/reject plans, authorize merges, direct which agent does what
- **Direct** — "Codex, review this plan." "Claude, fix the scratchpad." "Gemini, write a briefing on enrollment."
- **Sense** — "Something feels off about those line numbers." "Did we clean the index?"
- **Brainstorm** — "I have an idea about pilot tests..." (captured in designs)

None of these require a code editor. All of them fit in a text message.

## How It Could Work

**Input**: The operator sends text messages — questions, directives, approvals. These are routed to the appropriate agent or stored as decisions.

**Output**: Agents respond with summaries, not raw data. Bite-sized updates. Links to drill down when the operator is back at a desktop.

**Key interactions from a phone**:
- "What happened today?" → dev log summary
- "Show me the latest plan" → plan summary with approve/reject option
- "Codex, review the Memex refactor plan" → kicks off a Codex session
- "Approve the plan" → writes `decision.md`
- "Give me a bite on the grade cascade" → generates a 3-minute bite
- "Merge dev to main" → executes with confirmation
- "What's the status of the experiment?" → analysis summary

**What stays on the desktop**:
- Reading full plans (though summaries work on mobile)
- Code review of actual implementations
- Running experiments
- Anything requiring visual diff review

## Why This Matters

The constitutional architecture already moved the operator from "writing code" to "managing knowledge." The mobile console moves them from "managing knowledge at a desk" to "managing knowledge anywhere." The governance layer — plans, reviews, decisions, dev log — is the operator's interface. That interface is text. Text works on a phone.

This also changes the economics of operator attention. A 30-second check-in from a phone between meetings replaces a 10-minute context-switch back to a desktop. The operator stays in the loop with less friction.

## Open Questions

- What's the transport? SMS? Slack? A custom chat app? A thin wrapper around existing agent CLIs?
- How does authentication work for sensitive operations (merge, deploy)?
- How do agents know whether to send a full response or a mobile-optimized summary?
- Can the bite format serve as the default mobile output format?
- How does this interact with the notification system? (Agent finishes a task → operator gets a text)
