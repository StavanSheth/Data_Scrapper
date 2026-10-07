import { useEffect, useRef } from 'react';
import type { Run } from '../types';
import { fetchRun } from '../services/api';

export function useRunMonitor(
  activeRun: Run | null,
  onUpdate: (run: Run) => void,
  onProgress?: () => void
) {
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!activeRun) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const defaultWsBase = `${wsProtocol}//${window.location.host}/ws`;
    const wsBase = import.meta.env.VITE_WS_BASE_URL || defaultWsBase;
    const wsUrl = `${wsBase}/runs/${activeRun.id}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.run_id === activeRun.id) {
          onUpdate({ ...activeRun, ...msg });
          onProgress?.();
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    ws.onerror = () => {
      // WS error: handled by polling fallback below
    };

    const pollInterval = setInterval(async () => {
      if (['RUNNING', 'QUEUED'].includes(activeRun.status)) {
        try {
          const fresh = await fetchRun(activeRun.id);
          onUpdate(fresh);
          onProgress?.();
        } catch {
          // Ignore transient poll failures
        }
      }
    }, 3000);

    return () => {
      ws.close();
      clearInterval(pollInterval);
    };
  }, [activeRun?.id, activeRun?.status]);
}
