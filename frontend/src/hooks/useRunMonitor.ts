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

    let wsBase = import.meta.env.VITE_WS_BASE_URL;
    if (!wsBase) {
      const apiBase = import.meta.env.VITE_API_BASE_URL;
      if (apiBase && (apiBase.startsWith('http://') || apiBase.startsWith('https://'))) {
        wsBase = apiBase.replace(/^http/, 'ws').replace(/\/api\/?$/, '') + '/ws';
      } else if (window.location.port === '5173') {
        // Direct local development mode where backend runs on port 8000
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsBase = `${wsProtocol}//${window.location.hostname}:8000/ws`;
      } else {
        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsBase = `${wsProtocol}//${window.location.host}/ws`;
      }
    }

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
