/** WebSocket Hook */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { GenerationWsMessage } from '@/types/generation';
import { connectGenerationWs } from '@/api/ws';

interface UseWebSocketReturn {
  messages: GenerationWsMessage[];
  connected: boolean;
  connect: (taskId: string | number) => void;
  disconnect: () => void;
  clearMessages: () => void;
}

export function useWebSocket(): UseWebSocketReturn {
  const [messages, setMessages] = useState<GenerationWsMessage[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback((taskId: string | number) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = connectGenerationWs(
      taskId,
      (message) => {
        setMessages((prev) => [...prev.slice(-49), message]);
      },
      () => setConnected(false),
    );

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    wsRef.current = ws;
  }, []);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setConnected(false);
    }
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  return { messages, connected, connect, disconnect, clearMessages };
}
