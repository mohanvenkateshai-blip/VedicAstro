# MULTI-AGENT MANDATORY RULE (Enacted 2026-06-30)

**User directive (verbatim):** "MAKE IT A RULE TO START WITH 5 AGENTS MINIMUM AND SCALE UP IF NEEDED. ENACT THIS RULE NOW!!!"

This document + the Cursor rule at `.cursor/rules/multi-agent-mandatory-protocol.mdc` codify the protocol permanently.

## The Rule (in plain language)
- Every time you (the AI or any agent) begin meaningful work, you **MUST** immediately spawn **at least 5 sub-agents in parallel**.
- Use the `Task` tool (multiple calls in one go).
- Always include at least one "Multi-Agent Reminder / Orchestrator / Compliance" agent among the first wave.
- Scale up to 10, 20, or more as soon as the task size or user urgency ("FAAASSTTT", "do everything", "lightning speeds") indicates it.
- Never fall back to single-threaded, sequential, or "I'll do one thing then ask" mode.

## Why This Exists
The user has repeatedly expressed that:
- Sequential execution feels like the AI is "sleeping".
- They want true multi-agent lightning speed.
- They do not want to be asked questions before action.
- They specifically want a reminder agent that stays awake and forces the use of many agents.

## How It Is Enforced Going Forward
1. Cursor rule (`.cursor/rules/multi-agent-mandatory-protocol.mdc`) with `alwaysApply: true`.
2. This markdown file is the human-readable reference and is referenced in handoffs, CONTEXT.md, STATUS.md, etc.
3. At the beginning of every response involving work, the first actions are parallel `Task` launches (minimum 5).

## Current Enactment (this session)
As of this document creation:
- The Cursor rule file has been created and activated.
- Multiple agents are being launched in parallel right now for the ongoing knowledge organization + structured Gyan mapping work.
- A dedicated reminder/compliance agent will be part of the initial set.

**No more "where is the multi-agent reminder agent?"** — the protocol itself + explicit agent spawning at task start guarantees it.

If at any point you (future AI) or a sub-agent detects sequential behavior, you are required to stop and spawn additional agents immediately.

This is now project law.