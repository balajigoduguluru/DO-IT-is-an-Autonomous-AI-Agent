# Agentic AI Frontend Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform the Agentic AI project from a developer demo into a polished ChatGPT/Claude-like web application where the browser controls everything automatically.

**Architecture:** Keep the existing FastAPI backend entirely untouched (add one health endpoint). Rebuild the React SPA frontend with clean separation: `api/`, `context/`, `hooks/`, `components/`, `pages/`, `services/`, `types/`, `utils/` layers. Use Context + useReducer for global state. Dedicated WebSocket service with auto-reconnect and human-readable event translation. Developer mode toggle reveals technical details.

**Tech Stack:** React 18, Vite 5, TypeScript 5, Tailwind CSS 3, FastAPI (unchanged backend)

## Global Constraints

- The backend AI architecture (Planner, Supervisor, Evaluator, Scheduler, Execution Engine, Tool Registry, Memory, Risk Predictor, Approval System, LangGraph, WebSocket streaming) must NOT be modified
- The only backend change is adding `GET /api/health`
- No session IDs, API routes, DAGs, graphs, schedulers, tool registries, state machines, internal logs, JSON, or technical errors may be exposed in the default UI
- Every backend event must be translated to human-readable text
- The frontend must auto-orchestrate: health check → session creation → goal submission → execution start → WebSocket connection → live updates → final result
- All existing files at `frontend/src/api/client.ts`, `frontend/src/hooks/useWebSocket.ts`, and old components must be removed after replacement
- All new files go under `frontend/src/`

---

### Task 1: Add Backend Health Endpoint

**Files:**
- Modify: `src/api/routes.py` — add health endpoint

**Interfaces:**
- Consumes: (none)
- Produces: `GET /api/health` → `{"status": "ok", "timestamp": "..."}`

- [ ] **Step 1: Add the import and endpoint**

Add the `datetime` import and health endpoint to `src/api/routes.py`.

```python
# Add to imports at the top (not present yet):
from datetime import datetime, timezone

# Add before "Session endpoints" section:
@router.get("/health")
async def health_check():
    """Lightweight health check for frontend availability detection."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}
```

- [ ] **Step 2: Verify the endpoint works**

```bash
cd C:/Users/balaj/OneDrive/Documents/Projects/Agentic\ AI
curl -s http://localhost:8000/api/health 2>/dev/null || echo "Server not running — start with: uvicorn src.api.server:app --reload"
```

Expected: `{"status":"ok","timestamp":"2026-07-25T..."}`

---

### Task 2: Create Types, Event Translator, and Formatters

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/services/eventTranslator.ts`
- Create: `frontend/src/utils/formatters.ts`

**Interfaces:**
- Consumes: `src/core/constants.py` phases and statuses (conceptual reference)
- Produces: All TypeScript types used by every subsequent task; `translatePhase(phase: string): string`; `translateTaskType(taskType: string, status: string): string`; `translateError(error: string): string`; `formatTime(date: Date): string`

- [ ] **Step 1: Create type definitions**

Write `frontend/src/types/index.ts`:

```typescript
export type BackendStatus = 'checking' | 'online' | 'offline';

export type ExecutionStatus =
  | 'idle'
  | 'starting'
  | 'running'
  | 'awaiting_approval'
  | 'completed'
  | 'failed';

export interface ThinkingStep {
  id: string;
  text: string;
  status: 'pending' | 'current' | 'done' | 'error';
}

export interface Activity {
  id: string;
  time: string;
  text: string;
}

export interface ApprovalInfo {
  id: string;
  action: string;
  details?: Record<string, unknown>;
}

export interface ProgressInfo {
  current: number;
  total: number;
}

export interface ExecutionState {
  backendStatus: BackendStatus;
  status: ExecutionStatus;
  goal: string;
  currentTask: string;
  thinkingSteps: ThinkingStep[];
  progress: ProgressInfo | null;
  activities: Activity[];
  result: string | null;
  error: string | null;
  pendingApproval: ApprovalInfo | null;
  devMode: boolean;
}

// Dev-mode-only data
export interface DevModeData {
  sessionId: string | null;
  apiRequests: { method: string; path: string; timestamp: string }[];
  executionTimeMs: number | null;
  currentAgent: string | null;
  toolSelection: string | null;
  riskAnalysis: Record<string, unknown> | null;
  executionLedger: Record<string, unknown>[];
  memoryEvents: Record<string, unknown>[];
  websocketEvents: { type: string; data: unknown; timestamp: string }[];
  llmCalls: number;
  toolCalls: number;
  graphNodes: Record<string, unknown>;
  graphEdges: string[][];
  runningTasks: number;
  completedTasks: number;
  failedTasks: number;
}

export type ExecutionAction =
  | { type: 'SET_BACKEND_STATUS'; payload: BackendStatus }
  | { type: 'SET_EXECUTION_STATUS'; payload: ExecutionStatus }
  | { type: 'SET_GOAL'; payload: string }
  | { type: 'SET_CURRENT_TASK'; payload: string }
  | { type: 'ADD_THINKING_STEP'; payload: ThinkingStep }
  | { type: 'UPDATE_THINKING_STEP'; payload: { id: string; status: 'current' | 'done' | 'error' } }
  | { type: 'UPSERT_THINKING_STEP'; payload: ThinkingStep }
  | { type: 'SET_PROGRESS'; payload: ProgressInfo | null }
  | { type: 'ADD_ACTIVITY'; payload: Activity }
  | { type: 'SET_RESULT'; payload: string }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'SET_APPROVAL'; payload: ApprovalInfo }
  | { type: 'CLEAR_APPROVAL' }
  | { type: 'RESET' }
  | { type: 'TOGGLE_DEV_MODE' };

export type DevModeAction =
  | { type: 'SET_SESSION_ID'; payload: string }
  | { type: 'ADD_API_REQUEST'; payload: { method: string; path: string } }
  | { type: 'SET_EXECUTION_TIME'; payload: number | null }
  | { type: 'SET_CURRENT_AGENT'; payload: string | null }
  | { type: 'SET_TOOL_SELECTION'; payload: string | null }
  | { type: 'SET_RISK_ANALYSIS'; payload: Record<string, unknown> | null }
  | { type: 'SET_GRAPH_DATA'; payload: { nodes: Record<string, unknown>; edges: string[][] } }
  | { type: 'ADD_LEDGER_ENTRY'; payload: Record<string, unknown> }
  | { type: 'ADD_MEMORY_EVENT'; payload: Record<string, unknown> }
  | { type: 'ADD_WEBSOCKET_EVENT'; payload: { type: string; data: unknown } }
  | { type: 'INCREMENT_LLM_CALL' }
  | { type: 'INCREMENT_TOOL_CALL' }
  | { type: 'RESET_DEV' };

// Raw WebSocket event from backend
export interface WsEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}
```

- [ ] **Step 2: Create the event translator**

Write `frontend/src/services/eventTranslator.ts`:

```typescript
const PHASE_MAP: Record<string, string> = {
  UNDERSTAND_GOAL: 'Understanding your request…',
  CONSTRAIN: 'Identifying constraints…',
  PLANNING: 'Planning the best approach…',
  BUILD_DAG: 'Planning…',
  SCHEDULE: 'Organizing the work…',
  RISK_ANALYSIS: 'Checking for possible issues…',
  TOOL_SELECT: 'Choosing the best option…',
  EXECUTE: 'Working on your request…',
  EVALUATE: 'Checking the results…',
  REPLAN: 'Found a better approach…',
  APPROVAL: 'Waiting for your input…',
  SUMMARY: 'Generating final answer…',
  MEMORY_STORE: 'Learning from this task…',
  END: 'Done',
};

const TASK_ACTION_MAP: Record<string, Record<string, string>> = {
  running: {
    supervisor: 'Supervising execution…',
    planner: 'Planning next steps…',
    worker: 'Working…',
    evaluator: 'Evaluating quality…',
    default: 'Processing…',
  },
  completed: {
    flight: 'Flights found ✓',
    hotel: 'Hotels found ✓',
    train: 'Train schedules found ✓',
    weather: 'Weather checked ✓',
    budget: 'Budget calculated ✓',
    email: 'Email ready ✓',
    supervisor: 'Execution supervised ✓',
    planner: 'Plan created ✓',
    worker: 'Task complete ✓',
    evaluator: 'Quality check passed ✓',
    default: 'Completed ✓',
  },
};

export function translatePhase(phase: string): string {
  return PHASE_MAP[phase] ?? `Working…`;
}

export function translateCurrentTask(taskType: string, status: string): string {
  const statusMap = status === 'running' ? TASK_ACTION_MAP.running : TASK_ACTION_MAP.completed;
  const lowerType = taskType.toLowerCase();
  // Check for tool names like "flight_tool", "hotel_tool"
  for (const [key, value] of Object.entries(statusMap)) {
    if (lowerType.includes(key)) return value;
  }
  return statusMap.default;
}

export function translateTaskToActivity(taskType: string, status: string): string | null {
  if (status === 'running') return null; // Don't add activity for running, only completed
  const lowerType = taskType.toLowerCase();
  const activityMap: Record<string, Record<string, string>> = {
    completed: {
      flight: 'Found flights',
      hotel: 'Found hotels',
      train: 'Train schedules checked',
      weather: 'Weather checked',
      budget: 'Budget calculated',
      email: 'Email prepared',
      supervisor: 'Execution verified',
      planner: 'Plan created',
      evaluator: 'Quality verified',
      worker: 'Task done',
    },
    failed: {
      flight: 'Flight search failed — trying alternatives…',
      hotel: 'Hotel search failed — trying alternatives…',
      default: 'Something went wrong, retrying…',
    },
  };
  const map = status === 'failed' ? activityMap.failed : activityMap.completed;
  for (const [key, value] of Object.entries(map)) {
    if (lowerType.includes(key)) return value;
  }
  return status === 'failed' ? activityMap.failed.default : 'Completed';
}

export function translateError(error: string, recoverable: boolean): string {
  if (recoverable) {
    if (error.toLowerCase().includes('timeout')) return 'Something went wrong. Retrying…';
    if (error.toLowerCase().includes('rate')) return 'Too many requests. Slowing down…';
    return 'Something went wrong. Retrying…';
  }
  return 'I wasn\'t able to complete this. Please try again.';
}

export function translateApprovalAction(action: string): string {
  return action || 'proceed with the next step';
}
```

- [ ] **Step 3: Create formatters utility**

Write `frontend/src/utils/formatters.ts`:

```typescript
export function formatTime(date: Date): string {
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  return `${hours}:${minutes}`;
}

export function formatTimestamp(isoString: string): string {
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return isoString;
  return formatTime(date);
}

export function shortId(id: string): string {
  if (!id) return '';
  return id.length > 8 ? id.slice(0, 8) : id;
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.round((ms % 60000) / 1000);
  return `${minutes}m ${seconds}s`;
}

export function generateId(): string {
  return Math.random().toString(36).substring(2, 10);
}
```

---

### Task 3: Build API Service Layer

**Files:**
- Create: `frontend/src/api/api.ts`

**Interfaces:**
- Consumes: Types from Task 2
- Produces: `healthCheck(): Promise<boolean>`, `createSession(): Promise<string>`, `setGoal(sessionId, goal): Promise<void>`, `startExecution(sessionId): Promise<void>`, `respondApproval(sessionId, approvalId, approved): Promise<void>`, `getGraphData(sessionId): Promise<{nodes, edges}>`, `getLedger(sessionId): Promise<unknown[]>`

- [ ] **Step 1: Create the API client**

Write `frontend/src/api/api.ts`:

```typescript
const BASE = '/api';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const options: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) {
    options.body = JSON.stringify(body);
  }

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch (err) {
    throw new ApiError(0, 'Network error — is the server running?');
  }

  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      // keep default
    }
    throw new ApiError(res.status, detail);
  }

  const text = await res.text();
  if (!text) return {} as T;
  return JSON.parse(text) as T;
}

// ---- Public API ----

export async function healthCheck(): Promise<boolean> {
  try {
    const result = await request<{ status: string }>('GET', '/health');
    return result.status === 'ok';
  } catch {
    return false;
  }
}

export async function createSession(): Promise<string> {
  const result = await request<{ session_id: string }>('POST', '/session');
  return result.session_id;
}

export async function setGoal(sessionId: string, goal: string): Promise<void> {
  await request('POST', `/session/${sessionId}/goal`, {
    goal,
    constraints: {},
  });
}

export async function startExecution(sessionId: string): Promise<void> {
  await request('POST', `/session/${sessionId}/start`);
}

export async function respondApproval(
  sessionId: string,
  approvalId: string,
  approved: boolean,
): Promise<void> {
  await request('POST', `/approval/${sessionId}/respond`, {
    approval_id: approvalId,
    approved,
  });
}

export async function getGraphData(
  sessionId: string,
): Promise<{ nodes: Record<string, unknown>; edges: string[][] }> {
  return request('GET', `/session/${sessionId}/graph`);
}

export async function getLedger(sessionId: string): Promise<Record<string, unknown>[]> {
  const result = await request<{ entries: Record<string, unknown>[] }>(
    'GET',
    `/session/${sessionId}/ledger`,
  );
  return result.entries ?? [];
}
```

---

### Task 4: Build WebSocket Service

**Files:**
- Create: `frontend/src/api/websocket.ts`

**Interfaces:**
- Consumes: Types from Task 2, eventTranslator from Task 2
- Produces: `createWebSocketService(sessionId, callbacks): {close: () => void}` with auto-reconnect

- [ ] **Step 1: Create the WebSocket service**

Write `frontend/src/api/websocket.ts`:

```typescript
import type { WsEvent } from '../types';

export type WsStatus = 'connected' | 'connecting' | 'disconnected';

export interface WsCallbacks {
  onStatusChange: (status: WsStatus) => void;
  onPhaseChange: (phase: string) => void;
  onTaskUpdate: (taskId: string, status: string, output?: Record<string, unknown> | null) => void;
  onApprovalRequest: (approval: { id: string; action: string }) => void;
  onError: (taskId: string, error: string, recoverable: boolean) => void;
  onLedgerEntry: (entry: Record<string, unknown>) => void;
  onGraphUpdate: (nodes: Record<string, unknown>, edges: string[][]) => void;
  onRawEvent: (event: WsEvent) => void;
}

export function createWebSocketService(sessionId: string, callbacks: WsCallbacks) {
  let ws: WebSocket | null = null;
  let reconnectAttempts = 0;
  const MAX_RECONNECT = 5;
  let closed = false;
  let pingInterval: ReturnType<typeof setInterval> | null = null;

  function getReconnectDelay(): number {
    return Math.min(1000 * Math.pow(2, reconnectAttempts), 16000);
  }

  function connect() {
    if (closed) return;

    callbacks.onStatusChange('connecting');

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws/session/${sessionId}`;

    try {
      ws = new WebSocket(url);
    } catch {
      scheduleReconnect();
      return;
    }

    ws.onopen = () => {
      if (closed) return;
      reconnectAttempts = 0;
      callbacks.onStatusChange('connected');

      // Ping every 30s to keep connection alive
      pingInterval = setInterval(() => {
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: 'ping' }));
        }
      }, 30000);
    };

    ws.onmessage = (event: MessageEvent) => {
      if (closed) return;
      try {
        const raw: WsEvent = JSON.parse(event.data);
        callbacks.onRawEvent(raw);

        switch (raw.type) {
          case 'phase_change':
            callbacks.onPhaseChange((raw.data as { phase: string }).phase);
            break;
          case 'task_update': {
            const d = raw.data as { task_id: string; status: string; output?: Record<string, unknown> | null };
            callbacks.onTaskUpdate(d.task_id, d.status, d.output ?? null);
            break;
          }
          case 'approval_requested': {
            const d = raw.data as { id: string; action_description: string };
            callbacks.onApprovalRequest({ id: d.id, action: d.action_description });
            break;
          }
          case 'error': {
            const d = raw.data as { task_id: string; error: string; recoverable: boolean };
            callbacks.onError(d.task_id, d.error, d.recoverable);
            break;
          }
          case 'ledger_entry':
            callbacks.onLedgerEntry(raw.data as Record<string, unknown>);
            break;
          case 'graph_update': {
            const d = raw.data as { nodes: Record<string, unknown>; edges: string[][] };
            callbacks.onGraphUpdate(d.nodes ?? {}, d.edges ?? []);
            break;
          }
          case 'pong':
            // heartbeat response — no action needed
            break;
        }
      } catch {
        // Ignore malformed messages
      }
    };

    ws.onclose = () => {
      callbacks.onStatusChange('disconnected');
      if (pingInterval) clearInterval(pingInterval);
      pingInterval = null;
      scheduleReconnect();
    };

    ws.onerror = () => {
      ws?.close();
    };
  }

  function scheduleReconnect() {
    if (closed || reconnectAttempts >= MAX_RECONNECT) return;
    reconnectAttempts++;
    setTimeout(connect, getReconnectDelay());
  }

  function close() {
    closed = true;
    if (pingInterval) clearInterval(pingInterval);
    if (ws) {
      ws.close();
      ws = null;
    }
  }

  function send(data: unknown) {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  connect();

  return { close, send };
}
```

---

### Task 5: Build ExecutionContext (Global State)

**Files:**
- Create: `frontend/src/context/ExecutionContext.tsx`

**Interfaces:**
- Consumes: Types from Task 2
- Produces: `ExecutionProvider`, `useExecutionContext()`, `useDevModeContext()`, dispatch functions

- [ ] **Step 1: Create the ExecutionContext with reducer**

Write `frontend/src/context/ExecutionContext.tsx`:

```typescriptx
import React, { createContext, useContext, useReducer, useCallback } from 'react';
import type {
  ExecutionState,
  ExecutionAction,
  DevModeData,
  DevModeAction,
  BackendStatus,
  ExecutionStatus,
  ThinkingStep,
  Activity,
  ApprovalInfo,
  ProgressInfo,
} from '../types';
import { generateId } from '../utils/formatters';

// ---- Initial state ----

const initialExecutionState: ExecutionState = {
  backendStatus: 'checking',
  status: 'idle',
  goal: '',
  currentTask: '',
  thinkingSteps: [],
  progress: null,
  activities: [],
  result: null,
  error: null,
  pendingApproval: null,
  devMode: false,
};

const initialDevModeData: DevModeData = {
  sessionId: null,
  apiRequests: [],
  executionTimeMs: null,
  currentAgent: null,
  toolSelection: null,
  riskAnalysis: null,
  executionLedger: [],
  memoryEvents: [],
  websocketEvents: [],
  llmCalls: 0,
  toolCalls: 0,
  graphNodes: {},
  graphEdges: [],
  runningTasks: 0,
  completedTasks: 0,
  failedTasks: 0,
};

// ---- Reducers ----

function executionReducer(state: ExecutionState, action: ExecutionAction): ExecutionState {
  switch (action.type) {
    case 'SET_BACKEND_STATUS':
      return { ...state, backendStatus: action.payload };
    case 'SET_EXECUTION_STATUS':
      return { ...state, status: action.payload };
    case 'SET_GOAL':
      return { ...state, goal: action.payload };
    case 'SET_CURRENT_TASK':
      return { ...state, currentTask: action.payload };
    case 'ADD_THINKING_STEP':
      return {
        ...state,
        thinkingSteps: [...state.thinkingSteps, action.payload],
      };
    case 'UPDATE_THINKING_STEP':
      return {
        ...state,
        thinkingSteps: state.thinkingSteps.map((s) =>
          s.id === action.payload.id ? { ...s, status: action.payload.status } : s,
        ),
      };
    case 'UPSERT_THINKING_STEP': {
      const existing = state.thinkingSteps.findIndex((s) => s.id === action.payload.id);
      if (existing >= 0) {
        const newSteps = [...state.thinkingSteps];
        newSteps[existing] = { ...newSteps[existing], ...action.payload };
        return { ...state, thinkingSteps: newSteps };
      }
      return { ...state, thinkingSteps: [...state.thinkingSteps, action.payload] };
    }
    case 'SET_PROGRESS':
      return { ...state, progress: action.payload };
    case 'ADD_ACTIVITY':
      return {
        ...state,
        activities: [...state.activities, action.payload].slice(-50), // Keep last 50
      };
    case 'SET_RESULT':
      return { ...state, result: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_APPROVAL':
      return { ...state, pendingApproval: action.payload, status: 'awaiting_approval' };
    case 'CLEAR_APPROVAL':
      return { ...state, pendingApproval: null, status: 'running' };
    case 'RESET':
      return { ...initialExecutionState, backendStatus: state.backendStatus, devMode: state.devMode };
    case 'TOGGLE_DEV_MODE':
      return { ...state, devMode: !state.devMode };
    default:
      return state;
  }
}

function devReducer(state: DevModeData, action: DevModeAction): DevModeData {
  switch (action.type) {
    case 'SET_SESSION_ID':
      return { ...state, sessionId: action.payload };
    case 'ADD_API_REQUEST':
      return {
        ...state,
        apiRequests: [
          ...state.apiRequests,
          { ...action.payload, timestamp: new Date().toISOString() },
        ].slice(-100),
      };
    case 'SET_EXECUTION_TIME':
      return { ...state, executionTimeMs: action.payload };
    case 'SET_CURRENT_AGENT':
      return { ...state, currentAgent: action.payload };
    case 'SET_TOOL_SELECTION':
      return { ...state, toolSelection: action.payload };
    case 'SET_RISK_ANALYSIS':
      return { ...state, riskAnalysis: action.payload };
    case 'SET_GRAPH_DATA':
      return { ...state, graphNodes: action.payload.nodes, graphEdges: action.payload.edges };
    case 'ADD_LEDGER_ENTRY':
      return {
        ...state,
        executionLedger: [...state.executionLedger, action.payload].slice(-200),
      };
    case 'ADD_MEMORY_EVENT':
      return {
        ...state,
        memoryEvents: [...state.memoryEvents, action.payload].slice(-100),
      };
    case 'ADD_WEBSOCKET_EVENT':
      return {
        ...state,
        websocketEvents: [...state.websocketEvents, action.payload].slice(-200),
      };
    case 'INCREMENT_LLM_CALL':
      return { ...state, llmCalls: state.llmCalls + 1 };
    case 'INCREMENT_TOOL_CALL':
      return { ...state, toolCalls: state.toolCalls + 1 };
    case 'RESET_DEV':
      return { ...initialDevModeData };
    default:
      return state;
  }
}

// ---- Context ----

interface ExecutionContextValue {
  state: ExecutionState;
  devData: DevModeData;
  dispatch: React.Dispatch<ExecutionAction>;
  devDispatch: React.Dispatch<DevModeAction>;
}

const ExecutionCtx = createContext<ExecutionContextValue | null>(null);

export function ExecutionProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(executionReducer, initialExecutionState);
  const [devData, devDispatch] = useReducer(devReducer, initialDevModeData);

  return (
    <ExecutionCtx.Provider value={{ state, devData, dispatch, devDispatch }}>
      {children}
    </ExecutionCtx.Provider>
  );
}

export function useExecutionContext() {
  const ctx = useContext(ExecutionCtx);
  if (!ctx) throw new Error('useExecutionContext must be used within ExecutionProvider');
  return ctx;
}
```

---

### Task 6: Build useExecution Hook (Flow Orchestrator)

**Files:**
- Create: `frontend/src/hooks/useExecution.ts`

**Interfaces:**
- Consumes: api.ts (Task 3), websocket.ts (Task 4), ExecutionContext (Task 5), eventTranslator (Task 2)
- Produces: `{ startExecution, resetExecution, respondToApproval, isRunning }` — the single hook all UI components call

- [ ] **Step 1: Create the useExecution hook**

Write `frontend/src/hooks/useExecution.ts`:

```typescriptx
import { useCallback, useEffect, useRef } from 'react';
import { useExecutionContext } from '../context/ExecutionContext';
import * as api from '../api/api';
import { createWebSocketService } from '../api/websocket';
import type { WsCallbacks } from '../api/websocket';
import {
  translatePhase,
  translateCurrentTask,
  translateTaskToActivity,
  translateError,
  translateApprovalAction,
} from '../services/eventTranslator';
import { formatTime, generateId } from '../utils/formatters';

export function useExecution() {
  const { state, devData, dispatch, devDispatch } = useExecutionContext();
  const wsRef = useRef<{ close: () => void; send: (data: unknown) => void } | null>(null);
  const startTimeRef = useRef<number | null>(null);

  // ---- Health check on mount ----
  useEffect(() => {
    let cancelled = false;
    async function check() {
      const online = await api.healthCheck();
      if (!cancelled) {
        dispatch({ type: 'SET_BACKEND_STATUS', payload: online ? 'online' : 'offline' });
      }
    }
    check();
    const interval = setInterval(async () => {
      const online = await api.healthCheck();
      if (!cancelled) {
        dispatch({ type: 'SET_BACKEND_STATUS', payload: online ? 'online' : 'offline' });
      }
    }, 10000); // Re-check every 10s
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [dispatch]);

  // ---- Cleanup WS on unmount ----
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  // ---- Start execution ----
  const startExecution = useCallback(async (goal: string) => {
    if (!goal.trim()) return;

    dispatch({ type: 'SET_GOAL', payload: goal });
    dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'starting' });
    dispatch({ type: 'SET_ERROR', payload: '' });
    dispatch({ type: 'SET_RESULT', payload: '' });
    dispatch({ type: 'SET_CURRENT_TASK', payload: '' });
    dispatch({ type: 'SET_PROGRESS', payload: null });

    // Reset dev data for new session
    devDispatch({ type: 'RESET_DEV' });

    addActivity('Goal received');
    startTimeRef.current = Date.now();

    try {
      // Step 1: Create session
      devDispatch({ type: 'ADD_API_REQUEST', payload: { method: 'POST', path: '/session' } });
      const sessionId = await api.createSession();
      devDispatch({ type: 'SET_SESSION_ID', payload: sessionId });

      addActivity('Started planning');

      // Step 2: Set goal
      devDispatch({ type: 'ADD_API_REQUEST', payload: { method: 'POST', path: `/session/${sessionId}/goal` } });
      await api.setGoal(sessionId, goal);
      addThinkingStep('Understanding your request…', 'done');

      // Step 3: Start execution
      devDispatch({ type: 'ADD_API_REQUEST', payload: { method: 'POST', path: `/session/${sessionId}/start` } });
      await api.startExecution(sessionId);

      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'running' });

      // Step 4: Connect WebSocket
      addThinkingStep('Planning the best approach…', 'current');

      const wsCallbacks: WsCallbacks = {
        onStatusChange: (wsStatus) => {
          devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: { type: 'status_change', data: wsStatus } });
        },
        onPhaseChange: (phase) => {
          devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: { type: 'phase_change', data: phase } });
          handlePhaseChange(phase);
        },
        onTaskUpdate: (taskId, status, output) => {
          devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: { type: 'task_update', data: { taskId, status } } });
          handleTaskUpdate(taskId, status, output);
        },
        onApprovalRequest: (approval) => {
          dispatch({
            type: 'SET_APPROVAL',
            payload: {
              id: approval.id,
              action: translateApprovalAction(approval.action),
              details: { raw: approval.action },
            },
          });
          addActivity('Waiting for your approval…');
        },
        onError: (taskId, error, recoverable) => {
          const msg = translateError(error, recoverable);
          addActivity(msg);
          if (!recoverable) {
            dispatch({ type: 'SET_ERROR', payload: msg });
            dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'failed' });
            if (startTimeRef.current) {
              devDispatch({ type: 'SET_EXECUTION_TIME', payload: Date.now() - startTimeRef.current });
            }
          }
        },
        onLedgerEntry: (entry) => {
          devDispatch({ type: 'ADD_LEDGER_ENTRY', payload: entry });
          if ((entry.agent as string)?.toLowerCase().includes('memory')) {
            devDispatch({ type: 'ADD_MEMORY_EVENT', payload: entry });
          }
        },
        onGraphUpdate: (nodes, edges) => {
          devDispatch({ type: 'SET_GRAPH_DATA', payload: { nodes, edges } });
          // Count task statuses
          const nodeList = Object.values(nodes) as Array<{
            agent_type?: string;
            status?: string;
          }>;
          const running = nodeList.filter((n) => n.status === 'RUNNING').length;
          const completed = nodeList.filter((n) => n.status === 'COMPLETED').length;
          const failed = nodeList.filter((n) => n.status === 'FAILED').length;
          devDispatch({ type: 'SET_CURRENT_AGENT', payload: running > 0 ? nodeList.find((n) => n.status === 'RUNNING')?.agent_type ?? null : null });

          // Track dev data
          devData.runningTasks = running;
          devData.completedTasks = completed;
          devData.failedTasks = failed;
        },
        onRawEvent: () => {
          // Already handled via typed callbacks
        },
      };

      wsRef.current?.close();
      wsRef.current = createWebSocketService(sessionId, wsCallbacks);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Connection failed';
      dispatch({ type: 'SET_ERROR', payload: msg });
      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'failed' });
    }
  }, [dispatch, devDispatch]);

  // ---- Phase change handler ----
  function handlePhaseChange(phase: string) {
    const text = translatePhase(phase);
    dispatch({ type: 'SET_CURRENT_TASK', payload: text });

    // Phase-to-step mapping with ordering
    const phaseStepMap: Array<{ phases: string[]; id: string; text: string }> = [
      { phases: ['UNDERSTAND_GOAL', 'CONSTRAIN'], id: 'goal', text: 'Understanding your request…' },
      { phases: ['PLANNING', 'BUILD_DAG'], id: 'plan', text: 'Planning the best approach…' },
      { phases: ['SCHEDULE'], id: 'organize', text: 'Organizing the work…' },
      { phases: ['RISK_ANALYSIS'], id: 'check', text: 'Checking for possible issues…' },
      { phases: ['TOOL_SELECT'], id: 'choose', text: 'Choosing the best option…' },
      { phases: ['EXECUTE'], id: 'execute', text: 'Working on your request…' },
      { phases: ['EVALUATE'], id: 'evaluate', text: 'Checking the results…' },
      { phases: ['REPLAN'], id: 'replan', text: 'Found a better approach…' },
      { phases: ['APPROVAL'], id: 'approval', text: 'Waiting for your input…' },
      { phases: ['SUMMARY'], id: 'summary', text: 'Generating final answer…' },
      { phases: ['MEMORY_STORE'], id: 'learn', text: 'Learning from this task…' },
    ];

    let foundCurrent = false;
    for (const entry of phaseStepMap) {
      if (entry.phases.includes(phase)) {
        // This is the current step — upsert as 'current'
        dispatch({
          type: 'UPSERT_THINKING_STEP',
          payload: { id: entry.id, text: entry.text, status: 'current' },
        });
        foundCurrent = true;
      } else if (!foundCurrent) {
        // Previous steps — upsert as 'done'
        dispatch({
          type: 'UPSERT_THINKING_STEP',
          payload: { id: entry.id, text: entry.text, status: 'done' },
        });
      }
    }

    // Add activity for phase transitions
    const activityMap: Record<string, string> = {
      UNDERSTAND_GOAL: 'Started planning',
      PLANNING: 'Planning approach',
      BUILD_DAG: 'Creating execution plan',
      SCHEDULE: 'Organizing work',
      TOOL_SELECT: 'Choosing best options',
      EXECUTE: 'Started execution',
      EVALUATE: 'Checking results',
      REPLAN: 'Found a better approach',
      APPROVAL: 'Awaiting your input',
      SUMMARY: 'Preparing summary',
      END: 'Completed',
    };

    const activityText = activityMap[phase];
    if (activityText) {
      addActivity(activityText);
    }

    // Handle end state
    if (phase === 'END') {
      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'completed' });
      // Don't set result here — it will come from the graph data
      if (startTimeRef.current) {
        devDispatch({ type: 'SET_EXECUTION_TIME', payload: Date.now() - startTimeRef.current });
      }
      // Fetch final graph to get summary
      const sid = devData.sessionId;
      if (sid) {
        api.getGraphData(sid).then((graph) => {
          const nodes = Object.values(graph.nodes) as Array<{ output?: Record<string, unknown> | null; status?: string }>;
          const summaryNode = nodes.find((n) => n.output?.final_summary);
          if (summaryNode?.output?.final_summary) {
            dispatch({ type: 'SET_RESULT', payload: String(summaryNode.output.final_summary) });
          } else {
            // Fetch ledger for any final output
            api.getLedger(sid).then((entries) => {
              const lastEntry = entries[entries.length - 1];
              if (lastEntry?.details) {
                dispatch({ type: 'SET_RESULT', payload: JSON.stringify(lastEntry.details, null, 2) });
              }
            });
          }
        });
      }
    }

    // Progress: compute from phase order
    const phaseOrder = [
      'UNDERSTAND_GOAL', 'CONSTRAIN', 'PLANNING', 'BUILD_DAG',
      'SCHEDULE', 'RISK_ANALYSIS', 'TOOL_SELECT', 'EXECUTE',
      'EVALUATE', 'REPLAN', 'APPROVAL', 'SUMMARY', 'MEMORY_STORE', 'END',
    ];
    const idx = phaseOrder.indexOf(phase);
    if (idx >= 0) {
      dispatch({ type: 'SET_PROGRESS', payload: { current: idx + 1, total: phaseOrder.length } });
    }
  }

  // ---- Task update handler ----
  function handleTaskUpdate(taskId: string, status: string, output?: Record<string, unknown> | null) {
    const kind = (taskId || '').toLowerCase();
    const displayTask = translateCurrentTask(kind, status);
    dispatch({ type: 'SET_CURRENT_TASK', payload: displayTask });

    const activity = translateTaskToActivity(kind, status);
    if (activity) {
      addActivity(activity);
    }

    // Check for final summary in task output
    if (status === 'COMPLETED' && output?.final_summary) {
      dispatch({ type: 'SET_RESULT', payload: String(output.final_summary) });
    }

    // Track tool calls
    if (status === 'RUNNING') {
      // Check if this is a tool task
      const toolKeywords = ['flight', 'hotel', 'train', 'weather', 'budget', 'email'];
      if (toolKeywords.some((k) => kind.includes(k))) {
        devDispatch({ type: 'INCREMENT_TOOL_CALL' });
      } else {
        devDispatch({ type: 'INCREMENT_LLM_CALL' });
      }
    }
  }

  // ---- Helper functions ----
  function addActivity(text: string) {
    dispatch({
      type: 'ADD_ACTIVITY',
      payload: { id: generateId(), time: formatTime(new Date()), text },
    });
  }

  function addThinkingStep(text: string, status: 'current' | 'done') {
    dispatch({
      type: 'ADD_THINKING_STEP',
      payload: { id: generateId(), text, status },
    });
  }

  // ---- Respond to approval ----
  const respondToApproval = useCallback(async (approved: boolean) => {
    const approval = state.pendingApproval;
    const sessionId = devData.sessionId;
    if (!approval || !sessionId) return;

    try {
      if (wsRef.current) {
        wsRef.current.send({
          type: 'approval_response',
          approval_id: approval.id,
          approved,
        });
      } else {
        await api.respondApproval(sessionId, approval.id, approved);
      }
      dispatch({ type: 'CLEAR_APPROVAL' });
      addActivity(approved ? 'Approved — continuing…' : 'Cancelled — trying another way…');
    } catch {
      dispatch({ type: 'SET_ERROR', payload: 'Failed to send response. Please try again.' });
    }
  }, [state.pendingApproval, devData.sessionId, dispatch]);

  // ---- Reset ----
  const resetExecution = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    dispatch({ type: 'RESET' });
    devDispatch({ type: 'RESET_DEV' });
  }, [dispatch, devDispatch]);

  const isRunning = state.status === 'starting' || state.status === 'running';
  const isBusy = isRunning || state.status === 'awaiting_approval';
  const backendOnline = state.backendStatus === 'online';

  return {
    state,
    devData,
    startExecution,
    resetExecution,
    respondToApproval,
    isRunning,
    isBusy,
    backendOnline,
  };
}
```

---

### Task 7: Build UI Components (StatusCard, GoalInput, CurrentTask, ThinkingPanel, ProgressBar, ActivityFeed, ApprovalDialog)

**Files:**
- Create: `frontend/src/components/StatusCard.tsx`
- Create: `frontend/src/components/GoalInput.tsx`
- Create: `frontend/src/components/CurrentTask.tsx`
- Create: `frontend/src/components/ThinkingPanel.tsx`
- Create: `frontend/src/components/ProgressBar.tsx`
- Create: `frontend/src/components/ActivityFeed.tsx`
- Create: `frontend/src/components/ApprovalDialog.tsx`

**Interfaces:**
- Consumes: `useExecution()` hook (Task 6)
- Produces: Pure presentational components with Tailwind styling

- [ ] **Step 1: Create StatusCard**

Write `frontend/src/components/StatusCard.tsx`:

```typescriptx
import React from 'react';
import type { BackendStatus } from '../types';

interface Props {
  backendStatus: BackendStatus;
  devMode: boolean;
  onToggleDevMode: () => void;
}

export default function StatusCard({ backendStatus, devMode, onToggleDevMode }: Props) {
  const isOnline = backendStatus === 'online';

  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-lg font-semibold text-gray-900">AI Ready</span>
        <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-50 border border-green-200">
          <span className={`h-2 w-2 rounded-full ${isOnline ? 'bg-green-500' : 'bg-red-500'} ${isOnline ? '' : 'animate-pulse'}`} />
          <span className="text-xs font-medium text-green-700">
            {isOnline ? 'Connected' : 'Offline'}
          </span>
        </div>
      </div>
      <button
        onClick={onToggleDevMode}
        className={`text-xs px-3 py-1.5 rounded-lg border transition-colors ${
          devMode
            ? 'bg-primary/10 border-primary/30 text-primary'
            : 'bg-gray-50 border-gray-200 text-gray-400 hover:text-gray-600'
        }`}
      >
        ⚙ Dev Mode
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create GoalInput**

Write `frontend/src/components/GoalInput.tsx`:

```typescriptx
import React, { useState } from 'react';

interface Props {
  onSubmit: (goal: string) => void;
  disabled: boolean;
  backendOnline: boolean;
}

export default function GoalInput({ onSubmit, disabled, backendOnline }: Props) {
  const [goal, setGoal] = useState('');

  const handleSubmit = () => {
    if (!goal.trim() || disabled || !backendOnline) return;
    onSubmit(goal.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        What would you like me to help you with?
      </label>
      <div className="flex gap-3">
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Plan my Goa trip under ₹25,000..."
          disabled={disabled}
          className="flex-1 h-12 px-4 bg-white border border-gray-200 rounded-xl text-sm text-gray-900 placeholder-gray-400 shadow-sm focus:border-primary focus:ring-2 focus:ring-primary/20 focus:outline-none transition-all disabled:bg-gray-50 disabled:text-gray-400"
        />
        <button
          onClick={handleSubmit}
          disabled={!goal.trim() || disabled || !backendOnline}
          className="h-12 px-6 bg-primary text-white text-sm font-medium rounded-xl hover:bg-primary-600 disabled:bg-gray-200 disabled:text-gray-400 disabled:cursor-not-allowed transition-all shadow-sm hover:shadow flex items-center gap-2"
        >
          {disabled ? (
            <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          ) : (
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 010 1.971l-11.54 6.347a1.125 1.125 0 01-1.667-.985V5.653z" />
            </svg>
          )}
          Start AI
        </button>
      </div>
      {!backendOnline && (
        <p className="text-sm text-red-600 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
          Backend offline — please start the server
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Create CurrentTask**

Write `frontend/src/components/CurrentTask.tsx`:

```typescriptx
import React from 'react';

interface Props {
  task: string;
  visible: boolean;
}

export default function CurrentTask({ task, visible }: Props) {
  if (!visible || !task) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-1">
        Current Task
      </div>
      <div className="flex items-center gap-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-primary animate-pulse" />
        <span className="text-base font-medium text-gray-900">{task}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create ThinkingPanel**

Write `frontend/src/components/ThinkingPanel.tsx`:

```typescriptx
import React from 'react';
import type { ThinkingStep } from '../types';

interface Props {
  steps: ThinkingStep[];
  visible: boolean;
}

export default function ThinkingPanel({ steps, visible }: Props) {
  if (!visible || steps.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
        Thinking
      </div>
      <div className="space-y-2">
        {steps.map((step) => (
          <div key={step.id} className="flex items-center gap-2.5 text-sm">
            {step.status === 'done' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full bg-green-100 flex items-center justify-center">
                <svg className="h-3 w-3 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
              </span>
            )}
            {step.status === 'current' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full border-2 border-primary flex items-center justify-center">
                <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
              </span>
            )}
            {step.status === 'pending' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full border-2 border-gray-200" />
            )}
            {step.status === 'error' && (
              <span className="flex-shrink-0 h-5 w-5 rounded-full bg-red-100 flex items-center justify-center">
                <svg className="h-3 w-3 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </span>
            )}
            <span
              className={`${
                step.status === 'done'
                  ? 'text-gray-500'
                  : step.status === 'current'
                  ? 'text-gray-900 font-medium'
                  : step.status === 'error'
                  ? 'text-red-600'
                  : 'text-gray-300'
              }`}
            >
              {step.text}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Create ProgressBar**

Write `frontend/src/components/ProgressBar.tsx`:

```typescriptx
import React from 'react';
import type { ProgressInfo } from '../types';

interface Props {
  progress: ProgressInfo | null;
  visible: boolean;
}

export default function ProgressBar({ progress, visible }: Props) {
  if (!visible || !progress) return null;

  const { current, total } = progress;
  const pct = Math.round((current / total) * 100);

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="flex items-center justify-between mb-2">
        <div className="text-xs font-medium text-gray-400 uppercase tracking-wider">
          Progress
        </div>
        <span className="text-sm font-medium text-gray-600">
          Step {current} of {total}
        </span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all duration-500 ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create ActivityFeed**

Write `frontend/src/components/ActivityFeed.tsx`:

```typescriptx
import React, { useRef, useEffect } from 'react';
import type { Activity } from '../types';

interface Props {
  activities: Activity[];
  visible: boolean;
}

export default function ActivityFeed({ activities, visible }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [activities.length]);

  if (!visible || activities.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-4">
      <div className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-3">
        Activity
      </div>
      <div className="space-y-1.5 max-h-48 overflow-y-auto">
        {activities.map((activity) => (
          <div key={activity.id} className="flex items-start gap-2 text-sm">
            <span className="text-gray-400 font-mono text-xs mt-0.5 flex-shrink-0">
              {activity.time}
            </span>
            <span className="text-gray-700">{activity.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
```

- [ ] **Step 7: Create ApprovalDialog**

Write `frontend/src/components/ApprovalDialog.tsx`:

```typescriptx
import React from 'react';
import type { ApprovalInfo } from '../types';

interface Props {
  approval: ApprovalInfo | null;
  onRespond: (approved: boolean) => void;
}

export default function ApprovalDialog({ approval, onRespond }: Props) {
  if (!approval) return null;

  return (
    <div className="fixed inset-0 bg-black/30 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full mx-4 p-6 space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">👤</span>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Action Required</h3>
            <p className="text-sm text-gray-500 mt-0.5">
              {approval.action}
            </p>
          </div>
        </div>
        <p className="text-sm text-gray-700">
          I found the best option. Would you like me to continue?
        </p>
        <div className="flex gap-3 justify-end pt-2">
          <button
            onClick={() => onRespond(false)}
            className="px-5 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={() => onRespond(true)}
            className="px-5 py-2 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors shadow-sm"
          >
            Approve
          </button>
        </div>
      </div>
    </div>
  );
}
```

---

### Task 8: Build ResultPanel with Copy and Export

**Files:**
- Create: `frontend/src/components/ResultPanel.tsx`

**Interfaces:**
- Consumes: `useExecution()` hook
- Produces: Result display with Copy, New Goal, Export buttons

- [ ] **Step 1: Create ResultPanel**

Write `frontend/src/components/ResultPanel.tsx`:

```typescriptx
import React, { useState } from 'react';

interface Props {
  result: string | null;
  error: string | null;
  status: string;
  onNewGoal: () => void;
}

export default function ResultPanel({ result, error, status, onNewGoal }: Props) {
  const [copied, setCopied] = useState(false);

  if (!result && !error) return null;
  if (status !== 'completed' && status !== 'failed') return null;

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const textarea = document.createElement('textarea');
      textarea.value = result;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleExport = () => {
    if (!result) return;
    const blob = new Blob([result], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `agentic-ai-result-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="bg-white rounded-xl border border-red-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">😕</span>
          <div>
            <h3 className="text-base font-semibold text-gray-900">Something went wrong</h3>
            <p className="text-sm text-gray-500 mt-0.5">{error}</p>
          </div>
        </div>
        <button
          onClick={onNewGoal}
          className="px-5 py-2.5 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-xl">✨</span>
        <h3 className="text-base font-semibold text-gray-900">Final Answer</h3>
      </div>

      <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed whitespace-pre-wrap">
        {result}
      </div>

      <div className="flex gap-3 pt-2">
        <button
          onClick={handleCopy}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-1.5"
        >
          {copied ? (
            <>
              <svg className="h-4 w-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              Copied
            </>
          ) : (
            <>
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
              </svg>
              Copy
            </>
          )}
        </button>
        <button
          onClick={onNewGoal}
          className="px-4 py-2 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors"
        >
          New Goal
        </button>
        <button
          onClick={handleExport}
          className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors flex items-center gap-1.5"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
          Export
        </button>
      </div>
    </div>
  );
}
```

---

### Task 9: Build DevMode Panel

**Files:**
- Create: `frontend/src/components/DevModePanel.tsx`

**Interfaces:**
- Consumes: `useExecution()` hook devData
- Produces: Collapsible panel with DAG, session ID, ledger, metrics, etc.

- [ ] **Step 1: Create DevModePanel**

Write `frontend/src/components/DevModePanel.tsx`:

```typescriptx
import React, { useState } from 'react';
import type { DevModeData } from '../types';
import { formatTimestamp, formatDuration } from '../utils/formatters';

interface Props {
  devData: DevModeData;
  visible: boolean;
}

type DevTab = 'graph' | 'ledger' | 'events' | 'metrics';

export default function DevModePanel({ devData, visible }: Props) {
  const [activeTab, setActiveTab] = useState<DevTab>('graph');

  if (!visible) return null;

  const tabs: { key: DevTab; label: string }[] = [
    { key: 'graph', label: 'Graph' },
    { key: 'ledger', label: 'Ledger' },
    { key: 'events', label: 'Events' },
    { key: 'metrics', label: 'Metrics' },
  ];

  return (
    <div className="bg-white rounded-xl border border-amber-200 shadow-sm overflow-hidden">
      <div className="bg-amber-50 px-4 py-2 border-b border-amber-200">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-amber-800 uppercase tracking-wider">
            ⚙ Developer Mode
          </span>
          <span className="text-[10px] text-amber-600">
            Session: {devData.sessionId ? devData.sessionId.slice(0, 12) : '—'}
          </span>
          {devData.executionTimeMs && (
            <span className="text-[10px] text-amber-600 ml-auto">
              Time: {formatDuration(devData.executionTimeMs)}
            </span>
          )}
        </div>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-0 border-b border-gray-100 px-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.key
                ? 'text-primary border-b-2 border-primary'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="p-4 max-h-80 overflow-y-auto text-xs font-mono">
        {activeTab === 'graph' && (
          <div className="space-y-2">
            <div className="text-gray-400 mb-2">
              Nodes: {Object.keys(devData.graphNodes).length} | Edges: {devData.graphEdges.length}
            </div>
            {Object.entries(devData.graphNodes).slice(0, 20).map(([id, node]) => (
              <div key={id} className="flex items-center gap-2 text-gray-600">
                <span className="text-gray-400">{id.slice(0, 12)}</span>
                <span className="text-gray-300">|</span>
                <span className="text-gray-800">{(node as Record<string, string>)?.agent_type ?? '?'}</span>
                <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                  (node as Record<string, string>)?.status === 'COMPLETED' ? 'bg-green-100 text-green-700' :
                  (node as Record<string, string>)?.status === 'RUNNING' ? 'bg-blue-100 text-blue-700' :
                  (node as Record<string, string>)?.status === 'FAILED' ? 'bg-red-100 text-red-700' :
                  'bg-gray-100 text-gray-600'
                }`}>
                  {(node as Record<string, string>)?.status ?? 'PENDING'}
                </span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'ledger' && (
          <div className="space-y-1.5">
            {devData.executionLedger.length === 0 && (
              <span className="text-gray-400">No ledger entries yet</span>
            )}
            {devData.executionLedger.slice(-30).reverse().map((entry, i) => (
              <div key={i} className="flex items-start gap-2 text-gray-600">
                <span className="text-gray-400 flex-shrink-0">
                  {formatTimestamp((entry as Record<string, string>).timestamp ?? '')}
                </span>
                <span className="text-gray-300">|</span>
                <span className="font-medium text-gray-700">{(entry as Record<string, string>).agent ?? '?'}</span>
                <span className="text-gray-500">{(entry as Record<string, string>).action ?? ''}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'events' && (
          <div className="space-y-1.5">
            {devData.websocketEvents.length === 0 && (
              <span className="text-gray-400">No WebSocket events yet</span>
            )}
            {devData.websocketEvents.slice(-20).reverse().map((evt, i) => (
              <div key={i} className="text-gray-600">
                <span className="text-gray-400">{evt.timestamp.slice(11, 19)}</span>
                {' '}
                <span className="text-amber-700 font-medium">{evt.type}</span>
                {' '}
                <span className="text-gray-400">{JSON.stringify(evt.data).slice(0, 80)}</span>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'metrics' && (
          <div className="grid grid-cols-2 gap-3">
            <Metric label="Current Agent" value={devData.currentAgent ?? '—'} />
            <Metric label="Tool Selected" value={devData.toolSelection ?? '—'} />
            <Metric label="LLM Calls" value={String(devData.llmCalls)} />
            <Metric label="Tool Calls" value={String(devData.toolCalls)} />
            <Metric label="Running Tasks" value={String(devData.runningTasks)} />
            <Metric label="Completed" value={String(devData.completedTasks)} />
            <Metric label="Failed" value={String(devData.failedTasks)} />
            <Metric label="Execution Time" value={devData.executionTimeMs ? formatDuration(devData.executionTimeMs) : '—'} />
            <Metric label="API Requests" value={String(devData.apiRequests.length)} />
            <Metric label="Ledger Entries" value={String(devData.executionLedger.length)} />
            <Metric label="WS Events" value={String(devData.websocketEvents.length)} />
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-2.5">
      <div className="text-[10px] font-medium text-gray-400 uppercase tracking-wider">{label}</div>
      <div className="text-sm font-semibold text-gray-800 mt-0.5">{value}</div>
    </div>
  );
}
```

---

### Task 10: Build Dashboard Page and App Root

**Files:**
- Create: `frontend/src/pages/Dashboard.tsx`
- Modify: `frontend/src/App.tsx` (simplify to wrap with ExecutionProvider + render Dashboard)
- Modify: `frontend/src/main.tsx` (add ErrorBoundary)
- Create: `frontend/src/components/ErrorBoundary.tsx`

**Interfaces:**
- Consumes: All components from Tasks 7-9, useExecution hook from Task 6

- [ ] **Step 1: Create ErrorBoundary**

Write `frontend/src/components/ErrorBoundary.tsx`:

```typescriptx
import React, { Component } from 'react';

interface Props {
  children: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-8 max-w-md w-full text-center space-y-4">
            <span className="text-4xl">😕</span>
            <h2 className="text-lg font-semibold text-gray-900">Something went wrong</h2>
            <p className="text-sm text-gray-500">{this.state.error?.message ?? 'An unexpected error occurred.'}</p>
            <button
              onClick={() => window.location.reload()}
              className="px-5 py-2.5 text-sm font-medium text-white bg-primary hover:bg-primary-600 rounded-lg transition-colors"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
```

- [ ] **Step 2: Create Dashboard page**

Write `frontend/src/pages/Dashboard.tsx`:

```typescriptx
import React from 'react';
import { useExecution } from '../hooks/useExecution';
import { useExecutionContext } from '../context/ExecutionContext';
import StatusCard from '../components/StatusCard';
import GoalInput from '../components/GoalInput';
import CurrentTask from '../components/CurrentTask';
import ThinkingPanel from '../components/ThinkingPanel';
import ProgressBar from '../components/ProgressBar';
import ActivityFeed from '../components/ActivityFeed';
import ResultPanel from '../components/ResultPanel';
import ApprovalDialog from '../components/ApprovalDialog';
import DevModePanel from '../components/DevModePanel';

export default function Dashboard() {
  const { dispatch } = useExecutionContext();
  const {
    state,
    devData,
    startExecution,
    resetExecution,
    respondToApproval,
    isBusy,
    backendOnline,
  } = useExecution();

  const showLiveSections = state.status !== 'idle';
  const showResult = state.status === 'completed' || state.status === 'failed';

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
        {/* Status + Dev Mode toggle */}
        <StatusCard
          backendStatus={state.backendStatus}
          devMode={state.devMode}
          onToggleDevMode={() => dispatch({ type: 'TOGGLE_DEV_MODE' })}
        />

        {/* Goal Input — always visible */}
        <GoalInput
          onSubmit={startExecution}
          disabled={isBusy}
          backendOnline={backendOnline}
        />

        {/* Live sections — show during and after execution */}
        {showLiveSections && (
          <>
            <CurrentTask task={state.currentTask} visible={state.status === 'running'} />
            <ThinkingPanel steps={state.thinkingSteps} visible={showLiveSections} />
            <ProgressBar progress={state.progress} visible={showLiveSections && !showResult} />
            <ActivityFeed activities={state.activities} visible={showLiveSections} />
          </>
        )}

        {/* Result */}
        {showResult && (
          <ResultPanel
            result={state.result}
            error={state.error}
            status={state.status}
            onNewGoal={resetExecution}
          />
        )}

        {/* Dev Mode Panel — always at bottom when visible */}
        <DevModePanel devData={devData} visible={state.devMode} />
      </div>

      {/* Approval Dialog — rendered as overlay */}
      <ApprovalDialog
        approval={state.pendingApproval}
        onRespond={respondToApproval}
      />
    </div>
  );
}
```

Wait — `Dashboard.tsx` references `dispatch` without importing it. Let me fix that — it should use the context directly.

Actually, looking at this more carefully, `Dashboard.tsx` should get `dispatch` from the execution context. Let me restructure:

```typescriptx
import { useExecutionContext } from '../context/ExecutionContext';
// ...
const { dispatch } = useExecutionContext();
```

- [ ] **Step 3: Simplify App.tsx**

Write `frontend/src/App.tsx`:

```typescriptx
import { ExecutionProvider } from './context/ExecutionContext';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <ExecutionProvider>
      <Dashboard />
    </ExecutionProvider>
  );
}
```

- [ ] **Step 4: Update main.tsx with ErrorBoundary**

Write `frontend/src/main.tsx`:

```typescriptx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import ErrorBoundary from './components/ErrorBoundary';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>,
);
```

---

### Task 11: Clean Up Old Files and Styles

**Files:**
- Delete: `frontend/src/api/client.ts` (replaced by api.ts)
- Delete: `frontend/src/hooks/useWebSocket.ts` (replaced by websocket.ts)
- Delete: `frontend/src/components/DAGView.tsx` (folded into DevModePanel)
- Delete: `frontend/src/components/ExecutionLedger.tsx` (folded into DevModePanel)
- Delete: `frontend/src/components/ApprovalGate.tsx` (replaced by ApprovalDialog)
- Delete: `frontend/src/components/RiskPanel.tsx` (folded into DevModePanel)
- Delete: `frontend/src/components/LiveTimeline.tsx` (replaced by ThinkingPanel + ProgressBar)
- Modify: `frontend/src/styles/globals.css` (strip old dev-oriented styles)
- Modify: `frontend/index.html` (update title and meta)

- [ ] **Step 1: Remove unused dependencies**

```bash
cd C:/Users/balaj/OneDrive/Documents/Projects/Agentic\ AI/frontend
npm uninstall reactflow
```

- [ ] **Step 2: Clean up globals.css**

Write `frontend/src/styles/globals.css`:

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

body {
  font-family: 'Inter', sans-serif;
  background: #F9FAFB;
  color: #1F2937;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

* {
  box-sizing: border-box;
}

/* Custom scrollbar */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: #f1f1f1;
}
::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}
* {
  scrollbar-width: thin;
  scrollbar-color: #d1d5db #f1f1f1;
}
```

- [ ] **Step 3: Update index.html**

Write `frontend/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Agentic AI</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🤖</text></svg>" />
    <meta name="description" content="Agentic AI — Describe your goal, and AI handles the rest." />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 4: Delete old files**

```bash
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/api/client.ts"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/hooks/useWebSocket.ts"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/DAGView.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/ExecutionLedger.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/ApprovalGate.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/RiskPanel.tsx"
rm "C:/Users/balaj/OneDrive/Documents/Projects/Agentic AI/frontend/src/components/LiveTimeline.tsx"
```

---

### Task 12: Build and Verify

**Files:** (no new files — verification step)

- [ ] **Step 1: Start the backend**

```bash
cd C:/Users/balaj/OneDrive/Documents/Projects/Agentic\ AI
pip install -e . 2>/dev/null
uvicorn src.api.server:app --reload --port 8000
```

- [ ] **Step 2: Start the frontend**

In a new terminal:
```bash
cd C:/Users/balaj/OneDrive/Documents/Projects/Agentic\ AI/frontend
npm install 2>/dev/null
npm run dev
```

- [ ] **Step 3: Verify the application**

Open http://localhost:5173

Check:
- [ ] "AI Ready 🟢 Connected" appears
- [ ] Goal input and "Start AI" button are visible
- [ ] Clicking "Start AI" with a goal starts the flow
- [ ] Current Task updates in real time
- [ ] Thinking steps appear and update
- [ ] Progress shows "Step X of Y"
- [ ] Activity feed populates with human-readable entries
- [ ] Toggle "⚙ Dev Mode" reveals the developer panel
- [ ] When execution completes, Result shows with Copy / New Goal / Export
- [ ] "New Goal" resets to clean state
- [ ] No session IDs, API routes, or technical details visible in default mode
