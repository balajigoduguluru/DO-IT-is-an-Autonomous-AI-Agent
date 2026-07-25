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

