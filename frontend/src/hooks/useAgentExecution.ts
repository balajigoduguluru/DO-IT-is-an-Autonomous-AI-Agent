import { useEffect, useRef } from 'react';
import { useExecutionContext } from '../context/ExecutionContext';
import { 
  healthCheck, 
  createSession, 
  setGoal, 
  startExecution, 
  respondApproval 
} from '../api/api';
import { createWebSocketService } from '../api/websocket';
import { toast } from 'sonner';
import { translatePhase, translateCurrentTask, translateError } from '../utils/TerminologyMapper';
import { useHistory } from './useHistory';

const SESSION_STORAGE_KEY = 'doit_active_session';

export function useAgentExecution() {
  const { state, devData, dispatch, devDispatch } = useExecutionContext();
  const { addHistoryItem } = useHistory();
  const wsRef = useRef<ReturnType<typeof createWebSocketService> | null>(null);

  // 1. Health check and session resumption on mount
  useEffect(() => {
    let mounted = true;
    async function init() {
      const isOnline = await healthCheck();
      if (mounted) {
        dispatch({ type: 'SET_BACKEND_STATUS', payload: isOnline ? 'online' : 'offline' });
        if (!isOnline) {
          toast.error('Backend is offline. Please start the execution engine.', { duration: Infinity });
        } else {
          toast.success('Connected to DO IT execution engine.');
          
          // Check for existing session
          const savedSession = localStorage.getItem(SESSION_STORAGE_KEY);
          if (savedSession) {
            try {
              // We could fetch session status here to see if it's still running,
              // but for now we just reconnect the websocket to resume the feed.
              devDispatch({ type: 'SET_SESSION_ID', payload: savedSession });
              dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'running' });
              connectWebSocket(savedSession);
              toast.info('Resuming previous session...');
            } catch (err) {
              localStorage.removeItem(SESSION_STORAGE_KEY);
            }
          }
        }
      }
    }
    init();
    return () => { mounted = false; };
  }, [dispatch]);
  
  // Helper to connect WS
  const connectWebSocket = (sessionId: string) => {
    if (wsRef.current) wsRef.current.close();
    wsRef.current = createWebSocketService(sessionId, {
      onStatusChange: (status) => {
        if (status === 'disconnected') {
          toast.error('Lost connection, attempting to reconnect...');
        }
      },
      onMaxReconnectReached: () => {
        toast.error('Could not reconnect to the execution engine after multiple attempts.', { duration: Infinity });
        dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'failed' });
        dispatch({ type: 'SET_ERROR', payload: 'Connection permanently lost.' });
      },
      onPhaseChange: (phase) => {
        const translated = translatePhase(phase);
        dispatch({ 
          type: 'ADD_THINKING_STEP', 
          payload: { id: Date.now().toString(), text: translated, status: 'pending' }
        });
      },
      onTaskUpdate: (taskId, status, output) => {
        const translatedTask = translateCurrentTask(taskId);
        dispatch({ type: 'SET_CURRENT_TASK', payload: translatedTask });
        
        if (status === 'completed' && output?.result) {
          dispatch({ type: 'SET_RESULT', payload: output.result as string });
          dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'completed' });
          localStorage.removeItem(SESSION_STORAGE_KEY);
          toast.success('Mission completed successfully');
        }
      },
      onApprovalRequest: (approval) => {
        dispatch({ 
          type: 'SET_APPROVAL', 
          payload: { id: approval.id, action: approval.action }
        });
      },
      onError: (_taskId, error, recoverable) => {
        if (!recoverable) {
          dispatch({ type: 'SET_ERROR', payload: translateError(error) });
          dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'failed' });
          localStorage.removeItem(SESSION_STORAGE_KEY);
          toast.error('Mission failed critically');
        }
      },
      onLedgerEntry: (entry) => {
        dispatch({ 
          type: 'ADD_ACTIVITY', 
          payload: { id: Date.now().toString(), time: new Date().toISOString(), text: (entry.message as string) || 'System event' }
        });
      },
      onGraphUpdate: (nodes, edges) => {
        devDispatch({ type: 'SET_GRAPH_DATA', payload: { nodes, edges } });
      },
      onRawEvent: (event) => {
        devDispatch({ type: 'ADD_WEBSOCKET_EVENT', payload: event });
      }
    });
  };

  // 2. Main submission handler
  const submitGoal = async (goal: string, attachments: { type: string, file: File }[] = [], webSearchEnabled: boolean = false) => {
    if (state.backendStatus === 'offline') {
      toast.error('Cannot start mission: Backend is offline.');
      return;
    }

    try {
      dispatch({ type: 'SET_GOAL', payload: goal });
      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'running' });

      // Clean up any old WS
      if (wsRef.current) {
        wsRef.current.close();
      }

      // Automatically create session
      const sessionId = await createSession();
      devDispatch({ type: 'SET_SESSION_ID', payload: sessionId });
      localStorage.setItem(SESSION_STORAGE_KEY, sessionId);

      // Automatically connect WebSocket before starting execution to avoid missing events
      connectWebSocket(sessionId);

      // Build constraints payload from UI state
      const constraints: Record<string, any> = {};
      if (webSearchEnabled) {
        constraints.web_search_enabled = true;
      }
      
      // Handle file uploads if any
      if (attachments.length > 0) {
        import('../api/api').then(api => {
           api.uploadFiles(sessionId, attachments.map(a => a.file)).catch(e => {
               toast.error('Failed to upload some attachments.');
           });
        });
        constraints.attachments = attachments.map(a => ({ name: a.file.name, type: a.type, size: a.file.size }));
      }

      // Send Goal
      await setGoal(sessionId, goal, constraints);
      
      // Save dynamic history
      addHistoryItem(goal, `Started mission at ${new Date().toLocaleTimeString()}`);
      
      // Start Execution
      await startExecution(sessionId);

    } catch (err) {
      const error = err as Error;
      dispatch({ type: 'SET_ERROR', payload: error.message || 'Failed to initialize session' });
      dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'failed' });
      localStorage.removeItem(SESSION_STORAGE_KEY);
      toast.error('Mission initialization failed');
    }
  };

  // 3. Approval Response Handler
  const respondToApproval = async (approved: boolean) => {
    if (!devData.sessionId || !state.pendingApproval) return;
    
    try {
      await respondApproval(devData.sessionId, state.pendingApproval.id, approved);
      if (approved) {
        dispatch({ type: 'CLEAR_APPROVAL' });
        toast.success('Action approved. Mission resuming.');
      } else {
        dispatch({ type: 'SET_EXECUTION_STATUS', payload: 'failed' });
        dispatch({ type: 'SET_ERROR', payload: 'User rejected the action.' });
        toast.error('Action rejected. Mission aborted.');
      }
    } catch (err) {
      toast.error('Failed to submit approval response');
    }
  };

  return {
    submitGoal,
    respondToApproval,
    wsRef
  };
}
