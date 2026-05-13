---
description: Workflow routing for AL development requests — classify before implementing, propose route to user
---

# Workflow Routing

For any AL/BC development request, classify complexity **before** acting. Do not default to direct implementation in the main session — the `/plan` and `/develop` skills exist for a reason.

## Classification

| Tier | Criteria | Route |
|---|---|---|
| TRIVIAL | 1 file, obvious change (typo, single property flip, single field add) | Build directly OR `/fix` (Tier 1) |
| SIMPLE | 2-3 files, pattern already established in the codebase | `/fix` (Tier 2) or `/plan` → `/develop` |
| MEDIUM | 4-8 files, design decisions needed | `/plan` → `/develop` |
| COMPLEX | 9+ files, new architecture, or unclear requirements | `/interview` → `/plan` → `/develop` → `/test` |

## Procedure

1. **Classify silently.** Read the request, estimate the file count, gauge design uncertainty.

2. **Propose the route via `AskUserQuestion`** before doing anything else:

   > Classified as **<TIER>** — <one-line reason>.
   > Proposed route: **<command chain>** (~<time range>).
   >
   > Options:
   > - Use proposed route
   > - Build directly (skip skills)
   > - Different route (specify)
   > - Discuss requirements first

3. **Wait for confirmation** before invoking any skill, spawning agents, or writing code.

## Override Cases (skip the proposal)

- User explicitly invokes a skill (`/fix`, `/plan`, `/develop`, `/test`, `/interview`, `/document`) → run that skill directly.
- User says "just do it", "directly", "schnell", or similar → skip proposal, build.
- TRIVIAL one-line edits (typo, caption fix, property toggle) where asking would waste more time than fixing → build directly, mention the edit in the response.

## Why this rule exists

- `/plan` runs **competitive solution design** (2-3 architects with different starting constraints, debate, synthesis). Skipping it on MEDIUM/COMPLEX work means suboptimal designs ship.
- `/develop` runs the **4-specialist review team** (Security, AL-Expert, Performance, Test-Coverage) in parallel. Skipping it means defects ship.
- Direct implementation in the main session burns context that could be used for review and synthesis. **Delegate by default.**
- Without routing, requests like "add a credit limit check" silently turn into ad-hoc edits with no audit trail in `.dev/<task-slug>/`.
