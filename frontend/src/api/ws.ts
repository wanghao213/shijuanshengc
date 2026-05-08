/** WebSocket 管理 */

import type { GenerationWsMessage } from '@/types/generation';

type WsCallback = (message: GenerationWsMessage) => void;

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export function connectGenerationWs(
  taskId: string | number,
  onMessage: WsCallback,
  onError?: (error: Event) => void,
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/api/v1/generation/ws/${taskId}`);

  ws.onmessage = (event) => {
    try {
      const data: GenerationWsMessage = JSON.parse(event.data);
      onMessage(data);
    } catch {
      // ignore parse errors
    }
  };

  ws.onerror = (error) => {
    onError?.(error);
  };

  return ws;
}
