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
    }, 10000);
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

  // ---- Phase change handler ----
  function handlePhaseChange(phase: string) {
    const text = translatePhase(phase);
    dispatch({ type: 'SET_CURRENT_TASK', payload: text });

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
        dispatch({
          type: 'UPSERT_THINKING_STEP',
          payload: { id: entry.id, text: entry.text, status: 'current' },
        });
        foundCurrent = true;
      } else if (!foundCurrent) {
        dispatch({
          type: 'UPSERT_THINKING_STEP',
          payload: { id: entry.id, text: entry.text, status: 'done' },
        });
      }
    }

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

    if (phase === 'END') {
      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'completed' });
      if (startTimeRef.current) {
        devDispatch({ type: 'SET_EXECUTION_TIME', payload: Date.now() - startTimeRef.current });
      }
      const sid = devData.sessionId;
      if (sid) {
        api.getGraphData(sid).then((graph) => {
          const nodes = Object.values(graph.nodes) as Array<{ output?: Record<string, unknown> | null; status?: string }>;
          const summaryNode = nodes.find((n) => n.output?.final_summary);
          if (summaryNode?.output?.final_summary) {
            dispatch({ type: 'SET_RESULT', payload: String(summaryNode.output.final_summary) });
          } else {
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

    if (status === 'COMPLETED' && output?.final_summary) {
      dispatch({ type: 'SET_RESULT', payload: String(output.final_summary) });
    }

    if (status === 'RUNNING') {
      const toolKeywords = ['flight', 'hotel', 'train', 'weather', 'budget', 'email'];
      if (toolKeywords.some((k) => kind.includes(k))) {
        devDispatch({ type: 'INCREMENT_TOOL_CALL' });
      } else {
        devDispatch({ type: 'INCREMENT_LLM_CALL' });
      }
    }
  }

  // ---- Start execution ----
  const startExecution = useCallback(async (goal: string) => {
    if (!goal.trim()) return;

    dispatch({ type: 'SET_GOAL', payload: goal });
    dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'starting' });
    dispatch({ type: 'SET_ERROR', payload: '' });
    dispatch({ type: 'SET_RESULT', payload: '' });
    dispatch({ type: 'SET_CURRENT_TASK', payload: '' });
    dispatch({ type: 'SET_PROGRESS', payload: null });

    devDispatch({ type: 'RESET_DEV' });

    addActivity('Goal received');
    startTimeRef.current = Date.now();

    try {
      devDispatch({ type: 'ADD_API_REQUEST', payload: { method: 'POST', path: '/session' } });
      const sessionId = await api.createSession();
      devDispatch({ type: 'SET_SESSION_ID', payload: sessionId });

      addActivity('Started planning');

      devDispatch({ type: 'ADD_API_REQUEST', payload: { method: 'POST', path: `/session/${sessionId}/goal` } });
      await api.setGoal(sessionId, goal);
      addThinkingStep('Understanding your request…', 'done');

      devDispatch({ type: 'ADD_API_REQUEST', payload: { method: 'POST', path: `/session/${sessionId}/start` } });
      await api.startExecution(sessionId);

      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'running' });
      addThinkingStep('Planning the best approach…', 'current');

      const wsCallbacks: WsCallbacks = {
        onStatusChange: (wsStatus) => {
          devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: { type: 'status_change', data: wsStatus, timestamp: new Date().toISOString() } });
        },
        onPhaseChange: (phase) => {
          devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: { type: 'phase_change', data: phase, timestamp: new Date().toISOString() } });
          handlePhaseChange(phase);
        },
        onTaskUpdate: (taskId, status, output) => {
          devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: { type: 'task_update', data: { taskId, status }, timestamp: new Date().toISOString() } });
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
        onError: (_taskId, error, recoverable) => {
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
          const nodeList = Object.values(nodes) as Array<{
            agent_type?: string;
            status?: string;
          }>;
          const running = nodeList.filter((n) => n.status === 'RUNNING').length;
          devDispatch({
            type: 'SET_CURRENT_AGENT',
            payload: running > 0 ? nodeList.find((n) => n.status === 'RUNNING')?.agent_type ?? null : null,
          });
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
