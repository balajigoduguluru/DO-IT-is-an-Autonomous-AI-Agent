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

