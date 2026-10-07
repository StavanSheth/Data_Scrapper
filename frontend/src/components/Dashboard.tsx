import React from 'react';
import type { Run } from '../types';
import { StatusBadge } from './StatusBadge';
import {
  Database,
  CheckCircle2,
  AlertTriangle,
  Play,
  ArrowRight,
  Layers,
  MapPin,
} from 'lucide-react';

interface Props {
  runs: Run[];
  onSelectRun: (run: Run) => void;
  onNewRunClick: () => void;
}

export const Dashboard: React.FC<Props> = ({ runs, onSelectRun, onNewRunClick }) => {
  const totalRuns = runs.length;
  const completedRuns = runs.filter((r) => r.status === 'COMPLETED' || r.status === 'PARTIAL').length;
  const totalSaved = runs.reduce((acc, r) => acc + (r.records_saved || 0), 0);
  const totalFailed = runs.reduce((acc, r) => acc + (r.records_failed || 0), 0);

  return (
    <div className="space-y-6">
      {/* Top metrics cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Total Scraping Runs</span>
            <Layers className="w-4 h-4 text-slate-500" />
          </div>
          <p className="text-2xl font-bold text-slate-100 font-mono">{totalRuns}</p>
          <span className="text-[11px] text-slate-500 mt-1 block">Local run sessions</span>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Completed / Partial</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-500" />
          </div>
          <p className="text-2xl font-bold text-emerald-400 font-mono">{completedRuns}</p>
          <span className="text-[11px] text-slate-500 mt-1 block">Finished successfully</span>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Businesses Stored</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <p className="text-2xl font-bold text-slate-100 font-mono">{totalSaved}</p>
          <span className="text-[11px] text-slate-500 mt-1 block">Canonical entities in SQLite</span>
        </div>

        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 shadow-md">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-2">
            <span>Errors / Failed</span>
            <AlertTriangle className="w-4 h-4 text-amber-500" />
          </div>
          <p className="text-2xl font-bold text-amber-400 font-mono">{totalFailed}</p>
          <span className="text-[11px] text-slate-500 mt-1 block">Isolated record failures</span>
        </div>
      </div>

      {/* Recent runs table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h3 className="text-base font-semibold text-slate-100">Historical Scraping Runs</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Persistent search runs stored locally in SQLite database
            </p>
          </div>
          <button
            onClick={onNewRunClick}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium shadow-sm transition-colors"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Start New Run</span>
          </button>
        </div>

        {runs.length === 0 ? (
          <div className="p-12 text-center">
            <Database className="w-10 h-10 text-slate-600 mx-auto mb-3" />
            <h4 className="text-base font-semibold text-slate-200">No scraping runs yet</h4>
            <p className="text-xs text-slate-400 max-w-sm mx-auto mt-1 mb-5">
              Launch your first Google Maps scraping run to discover, normalize, and inspect local businesses.
            </p>
            <button
              onClick={onNewRunClick}
              className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold shadow-md transition-colors"
            >
              Configure First Run
            </button>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="bg-slate-950/60 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Location & Category</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-center">Discovered</th>
                  <th className="py-3 px-4 text-center">Saved</th>
                  <th className="py-3 px-4 text-center">Failed</th>
                  <th className="py-3 px-4">Created At</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-200">
                {runs.map((r) => (
                  <tr
                    key={r.id}
                    onClick={() => onSelectRun(r)}
                    className="hover:bg-slate-800/50 cursor-pointer transition-colors"
                  >
                    <td className="py-3 px-4 font-mono font-medium text-slate-300">
                      {r.id.substring(0, 18)}...
                    </td>

                    <td className="py-3 px-4">
                      <div className="font-semibold text-slate-100 flex items-center space-x-1.5">
                        <MapPin className="w-3.5 h-3.5 text-emerald-400" />
                        <span>{r.city_input}</span>
                      </div>
                      <span className="text-[11px] text-slate-400">{r.category || 'All'}</span>
                    </td>

                    <td className="py-3 px-4">
                      <StatusBadge status={r.status} />
                    </td>

                    <td className="py-3 px-4 text-center font-mono">{r.records_discovered}</td>
                    <td className="py-3 px-4 text-center font-mono font-bold text-emerald-400">
                      {r.records_saved}
                    </td>
                    <td className="py-3 px-4 text-center font-mono text-amber-400">
                      {r.records_failed}
                    </td>

                    <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                      {new Date(r.created_at).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRun(r);
                        }}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-colors"
                      >
                        <ArrowRight className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
