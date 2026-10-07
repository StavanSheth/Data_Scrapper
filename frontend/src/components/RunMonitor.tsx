import React, { useEffect, useState } from 'react';
import type { Run } from '../types';
import { StatusBadge } from './StatusBadge';
import { MapPin, Square, Clock, CheckCircle2, AlertTriangle, Eye, Loader2 } from 'lucide-react';

interface Props {
  run: Run;
  onCancel: () => void;
  onViewResults: () => void;
}

export const RunMonitor: React.FC<Props> = ({ run, onCancel, onViewResults }) => {
  const [elapsed, setElapsed] = useState<string>('0s');

  useEffect(() => {
    if (!run.started_at) {
      setElapsed('Pending');
      return;
    }

    const start = new Date(run.started_at).getTime();
    const updateElapsed = () => {
      const end = run.completed_at ? new Date(run.completed_at).getTime() : Date.now();
      const diffSec = Math.floor((end - start) / 1000);
      if (diffSec < 60) {
        setElapsed(`${diffSec}s`);
      } else {
        const mins = Math.floor(diffSec / 60);
        const secs = diffSec % 60;
        setElapsed(`${mins}m ${secs}s`);
      }
    };

    updateElapsed();
    if (run.status === 'RUNNING' || run.status === 'QUEUED') {
      const interval = setInterval(updateElapsed, 1000);
      return () => clearInterval(interval);
    }
  }, [run.started_at, run.completed_at, run.status]);

  const isTerminal = ['COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED'].includes(run.status);
  const totalProcessed = (run.records_saved || 0) + (run.records_failed || 0);
  const percentage = isTerminal
    ? 100
    : Math.min(
        100,
        run.requested_limit > 0
          ? Math.round((totalProcessed / run.requested_limit) * 100)
          : 0
      );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl mb-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800">
        <div>
          <div className="flex items-center space-x-3 mb-1.5">
            <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
              <span className="text-emerald-400">{run.city_input}</span>
              <span className="text-slate-500">•</span>
              <span>{run.category || 'All Businesses'}</span>
            </h2>
            <StatusBadge status={run.status} />
          </div>
          <p className="text-xs text-slate-400 font-mono">Run ID: {run.id}</p>
        </div>

        <div className="flex items-center space-x-3">
          {!isTerminal && (
            <button
              onClick={onCancel}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-red-500/30 text-red-400 hover:bg-red-500/10 text-xs font-medium transition-colors"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Cancel Run</span>
            </button>
          )}

          <button
            onClick={onViewResults}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-sm transition-colors"
          >
            <Eye className="w-3.5 h-3.5" />
            <span>View Businesses</span>
          </button>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="my-5">
        <div className="flex items-center justify-between text-xs mb-2">
          <div className="flex items-center space-x-2">
            {run.status === 'RUNNING' && <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin" />}
            <span className="font-semibold text-slate-300">
              {run.records_saved} of {run.requested_limit} businesses processed
            </span>
          </div>
          <span className="font-mono font-bold text-emerald-400 text-sm">{percentage}%</span>
        </div>
        <div className="w-full h-2.5 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
          <div
            className={`h-full transition-all duration-300 ${
              run.status === 'PARTIAL'
                ? 'bg-amber-500'
                : run.status === 'FAILED'
                ? 'bg-red-500'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Discovered</span>
            <MapPin className="w-3.5 h-3.5 text-slate-500" />
          </div>
          <p className="text-xl font-bold text-slate-100 font-mono">{run.records_discovered}</p>
          <span className="text-[10px] text-slate-500">Google Maps place cards</span>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Saved in DB</span>
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          </div>
          <p className="text-xl font-bold text-emerald-400 font-mono">{run.records_saved}</p>
          <span className="text-[10px] text-slate-500">Normalized & validated</span>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Failed / Dropped</span>
            <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
          </div>
          <p className="text-xl font-bold text-amber-400 font-mono">{run.records_failed}</p>
          <span className="text-[10px] text-slate-500">Malformed or non-viable</span>
        </div>

        <div className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-1">
            <span>Elapsed Time</span>
            <Clock className="w-3.5 h-3.5 text-slate-500" />
          </div>
          <p className="text-xl font-bold text-slate-100 font-mono">{elapsed}</p>
          <span className="text-[10px] text-slate-500">
            {run.completed_at ? 'Run completed' : 'In progress'}
          </span>
        </div>
      </div>

      {run.error_message && (
        <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
          <strong>Notice:</strong> {run.error_message}
        </div>
      )}
    </div>
  );
};
