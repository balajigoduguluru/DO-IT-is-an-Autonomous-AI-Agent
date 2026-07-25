import React, { createContext, useContext, useReducer } from 'react';
import type {
  ExecutionState,
  ExecutionAction,
  DevModeData,
  DevModeAction,
} from '../types';

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
