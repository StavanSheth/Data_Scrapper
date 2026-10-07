import { useState, useEffect, useCallback } from 'react';
import type { Run, CreateRunPayload } from '../types';
import { fetchRuns, createRun as apiCreateRun, cancelRun as apiCancelRun, checkHealth } from '../services/api';

export function useRuns() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [isHealthy, setIsHealthy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchRuns();
      setRuns(data);
    } catch (err: any) {
      const msg = err?.message || 'Failed to load runs';
      setError(msg);
      console.error('Failed to load runs:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const ping = () => {
      checkHealth().then(() => setIsHealthy(true)).catch(() => setIsHealthy(false));
    };
    ping();
    const interval = setInterval(ping, 15000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  const createNewRun = async (payload: CreateRunPayload): Promise<Run> => {
    const newRun = await apiCreateRun(payload);
    setActiveRun(newRun);
    await loadRuns();
    return newRun;
  };

  const cancelActiveRun = async (runId: string): Promise<Run> => {
    const updated = await apiCancelRun(runId);
    setActiveRun((prev) => (prev && prev.id === runId ? updated : prev));
    await loadRuns();
    return updated;
  };

  return {
    runs,
    setRuns,
    activeRun,
    setActiveRun,
    isHealthy,
    loading,
    error,
    loadRuns,
    createNewRun,
    cancelActiveRun,
  };
}
