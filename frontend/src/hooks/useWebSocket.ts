import { useEffect, useRef, useState, useCallback } from 'react';

export type WebSocketStatus = 'disconnected' | 'connecting' | 'connected';

export function useWebSocket(sessionId: string | null): {
  status: WebSocketStatus;
  lastMessage: unknown;
  messages: unknown[];
  send: (data: unknown) => void;
} {
  const [status, setStatus] = useState<WebSocketStatus>('disconnected');
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const [messages, setMessages] = useState<unknown[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );
  const mountedRef = useRef(true);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    if (!sessionId) {
      setStatus('disconnected');
      return;
    }

    let ws: WebSocket | null = null;

    function connect() {
      if (!mountedRef.current || !sessionId) return;

      setStatus('connecting');

      try {
        ws = new WebSocket(`ws://localhost:8000/ws/session/${sessionId}`);
        wsRef.current = ws;

        ws.onopen = () => {
          if (mountedRef.current && ws === wsRef.current) {
            setStatus('connected');
          }
        };

        ws.onmessage = (event: MessageEvent) => {
          if (!mountedRef.current || ws !== wsRef.current) return;
          try {
            const data = JSON.parse(event.data);
            setLastMessage(data);
            setMessages((prev) => [...prev, data]);
          } catch {
            // If not valid JSON, still store the raw message
            const raw = { raw: event.data };
            setLastMessage(raw);
            setMessages((prev) => [...prev, raw]);
          }
        };

        ws.onclose = () => {
          if (!mountedRef.current) return;
          setStatus('disconnected');
          // Auto-reconnect after 2 seconds
          if (ws === wsRef.current) {
            reconnectTimeoutRef.current = setTimeout(() => {
              if (mountedRef.current && sessionId) {
                connect();
              }
            }, 2000);
          }
        };

        ws.onerror = () => {
          // onclose will fire after onerror, so we let that handle reconnection
          ws?.close();
        };
      } catch (err) {
        if (mountedRef.current) {
          setStatus('disconnected');
          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current && sessionId) {
              connect();
            }
          }, 2000);
        }
      }
    }

    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (ws) {
        ws.close();
        wsRef.current = null;
      }
    };
  }, [sessionId]);

  return { status, lastMessage, messages, send };
}
