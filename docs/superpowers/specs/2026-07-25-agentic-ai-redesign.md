# Agentic AI Redesign: Production Web Application

**Date:** 2026-07-25
**Status:** Approved Design

## Overview

Transform the existing Agentic AI project from a developer demo into a polished
production-style web application. The experience should feel like ChatGPT, Claude,
or Gemini — a normal user understands the interface within 10 seconds.

No curl, no Postman, no API testing, no session IDs, no terminal commands after
starting the development server. Everything happens automatically from the browser.

The backend remains the brain — all existing business logic is preserved untouched.

## Architecture

```
┌──────────────────────────────────────┐     HTTP/WS      ┌──────────────────────────────┐
│  FastAPI Backend (untouched)          │◄───────────────►│  React SPA                    │
│                                       │                  │                              │
│  Existing modules preserved:          │                  │  Auto-orchestrates:           │
│  • Planner / Supervisor / Evaluator   │                  │  1. Health check             │
│  • Task Scheduler                     │                  │  2. Create session           │
│  • Execution Graph & DAG builder      │                  │  3. Send goal                │
│  • Tool Registry (flight, hotel, …)  │                  │  4. Start execution          │
│  • Approval Gate                      │                  │  5. Connect WebSocket        │
│  • Memory (Learning, Plan)            │                  │  6. Receive live updates     │
│  • Risk Predictor                     │                  │  7. Display final answer     │
│  • WebSocket EventStreamer            │                  │                              │
│                                       │                  │  Never expose these steps.   │
│  One addition:                        │                  │                              │
│  • GET /api/health → {"status":"ok"}  │                  │  No session IDs shown.        │
└──────────────────────────────────────┘                  └──────────────────────────────┘
```

### Backend (FastAPI) — No Changes to Business Logic

**New endpoint only:** `GET /api/health` → `{"status": "ok"}`

All existing endpoints remain. The frontend calls them automatically and invisibly.

## User Flow (Fully Automatic)

| Step | Frontend Action | User Sees |
|------|----------------|-----------|
| Page loads | `GET /api/health` | "AI Ready 🟢 Connected" |
| User types goal + clicks Start AI | Create session → Send goal → Start → Open WS | Thinking panel appears |
| Execution runs | WebSocket events → human-readable text | Live activity + progress |
| Execution completes | Final result displayed | Beautiful answer with Copy / New Goal / Export |
| "New Goal" clicked | Reset state, new session | Clean slate |

## Main Dashboard

Only these sections are shown:

```
──────────────────────────────────────
AI Ready                    ⚙ Dev Mode
🟢 Connected
──────────────────────────────────────

What would you like me to help you with?

[____________________________________]

            Start AI

──────────────────────────────────────

Current Task

Searching hotels...

──────────────────────────────────────

Thinking

✓ Understanding your request
✓ Planning the best approach
⏳ Comparing options

──────────────────────────────────────

Progress

Step 3 of 6

──────────────────────────────────────

Activity

10:01 Goal received
10:02 Started planning
10:03 Hotels found
10:04 Flight unavailable
10:04 Switched to train
10:05 Completed

──────────────────────────────────────

Result

(Display final answer beautifully)
```

## Simplified Thinking — Event Translation

| Raw Backend Event | User-Facing Display |
|---|---|
| UNDERSTAND_GOAL | Understanding your request… |
| PLANNING | Planning the best approach… |
| BUILD_DAG | Planning… |
| SCHEDULE | Organizing the work… |
| RISK_ANALYSIS | Checking for possible issues… |
| TOOL_SELECT | Choosing the best option… |
| EXECUTE | Working on your request… |
| EVALUATE | Checking the results… |
| REPLAN | Found a better approach… |
| APPROVAL | Waiting for your input… |
| MEMORY_STORE | Learning from this task… |
| END | Done |

## Current Task Display

Always show one current action, updated in real time:

- Searching hotels…
- Comparing flight prices…
- Preparing email…
- Generating report…
- Waiting for your approval…

This is the most prominent live-updating element.

## Progress

Use "Step X of Y" format, not fake percentages.

- Step 1 of 6
- Step 4 of 6
- Finalizing…

Only use percentages if computed from actual execution progress.

## Activity Feed

Write activity like a human. Examples:

| Good | Bad |
|---|---|
| Started planning | Execution supervised |
| Searching hotels | Scheduler completed |
| Found flights | Planner invoked |
| Compared prices | Task completed |
| Found a better option | Graph mutated |
| Preparing summary | Ledger updated |
| Completed | Memory stored |

## Approval Flow

Keep the existing backend approval system. Simplify the UI:

```
┌─────────────────────────────────────┐
│  I found the best option.           │
│  Would you like me to continue?     │
│                                     │
│      [ Approve ]  [ Cancel ]        │
└─────────────────────────────────────┘
```

Never show: "Approval Gate", "Human In The Loop", "Risk Threshold".
Execution automatically resumes after approval.

## Error Handling

Never expose technical errors:

| Technical → User-Friendly |
|---|
| "ToolRegistry timeout" → "Something went wrong. Retrying…" |
| "ExecutionGraph mutation failed" → "I found another way to continue." |
| (Recovery succeeds) → "Recovered automatically. Continuing…" |
| (Fatal) → "I wasn't able to complete this. Please try again." |

## Result Display

When finished, show:

```
──────────────────────────────────────

Final Answer

[Beautifully formatted result]

[ Copy ]  [ New Goal ]  [ Export ]
──────────────────────────────────────
```

## Developer Mode

Small toggle in the top-right corner: `⚙ Developer Mode`

**Default: OFF**
Only the clean dashboard is shown.

**When ON:**
Reveals a collapsible panel at the bottom containing:

- Execution Graph (DAG visualization)
- Current Agent
- Tool Selection
- Risk Analysis
- Execution Ledger
- Memory Events
- WebSocket Events
- Session ID
- API Requests
- Execution Time
- LLM Calls
- Tool Calls

For debugging and hackathon demonstrations only. Normal users never need it.

## Frontend Architecture

```
frontend/src/
  api/
    api.ts              # Fetch-based API client
    websocket.ts        # WebSocket service + event translation
  context/
    ExecutionContext.tsx  # Global state via Context + useReducer
  hooks/
    useExecution.ts      # Orchestrates the full flow
  components/
    GoalInput.tsx        # Input + Start AI button
    StatusCard.tsx       # AI Ready / 🟢 Connected / 🔴 Offline
    CurrentTask.tsx      # Live current action display
    ThinkingPanel.tsx    # ✓ / ⏳ thinking steps
    ProgressBar.tsx      # Step X of Y
    ActivityFeed.tsx     # Human-readable activity log
    ResultPanel.tsx      # Final answer + Copy / New Goal / Export
    ApprovalDialog.tsx   # Simplified approval modal
    DevModePanel.tsx     # Collapsible developer panel
    ErrorBoundary.tsx    # Graceful error handling
  pages/
    Dashboard.tsx        # Composes all components
  services/
    eventTranslator.ts   # Raw event → human-readable text
  types/
    index.ts             # TypeScript type definitions
  utils/
    formatters.ts        # Date, text formatting helpers
  App.tsx                # Root
  main.tsx               # Entry point
  styles/
    index.css            # Tailwind imports + global styles
```

Keep components reusable. Keep business logic outside components.
Use Context + Reducer for execution state. Separate presentation from logic.

## Non-Goals

- No authentication / login
- No session persistence across refresh (in-memory only)
- Mobile-responsive: desktop-first v1
- Dark mode: future enhancement
- No frontend tests in v1 (manual testing)
- No backend changes beyond `/api/health`
