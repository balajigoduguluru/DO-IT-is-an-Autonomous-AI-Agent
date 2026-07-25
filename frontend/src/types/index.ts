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
  | { type: 'ADD_WEBSOCKET_EVENT'; payload: { type: string; data: unknown; timestamp: string } }
  | { type: 'INCREMENT_LLM_CALL' }
  | { type: 'INCREMENT_TOOL_CALL' }
  | { type: 'RESET_DEV' };

// Raw WebSocket event from backend
export interface WsEvent {
  type: string;
  data: Record<string, unknown>;
  timestamp: string;
}
