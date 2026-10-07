import React from 'react';
import { Database, Plus, RefreshCw } from 'lucide-react';

interface Props {
  onNewRunClick: () => void;
  onRefresh: () => void;
  onDashboardClick: () => void;
  isHealthy: boolean;
}

export const Navbar: React.FC<Props> = ({
  onNewRunClick,
  onRefresh,
  onDashboardClick,
  isHealthy,
}) => {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div
          onClick={onDashboardClick}
          className="flex items-center space-x-3 cursor-pointer group"
        >
          <div className="w-10 h-10 rounded-lg bg-emerald-900/50 border border-emerald-600/40 flex items-center justify-center text-emerald-400 group-hover:border-emerald-500 transition-colors">
            <Database className="w-5 h-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-100 text-lg tracking-tight">
                Mavon Intelligence
              </span>
              <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Slice 1
              </span>
            </div>
            <p className="text-xs text-slate-400">Local Business Intelligence Scraper</p>
          </div>
        </div>

        <div className="flex items-center space-x-3">
          {/* Health status */}
          <div className="flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-900 border border-slate-800 text-slate-300">
            <span
              className={`w-2 h-2 rounded-full ${
                isHealthy ? 'bg-emerald-400 shadow-sm shadow-emerald-500/50' : 'bg-red-400'
              }`}
            />
            <span>{isHealthy ? 'Core Engine Online' : 'Connecting...'}</span>
          </div>

          <button
            onClick={onRefresh}
            title="Refresh runs list"
            className="p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-900 rounded-lg border border-transparent hover:border-slate-800 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            onClick={onNewRunClick}
            className="flex items-center space-x-2 px-3.5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm shadow-sm shadow-emerald-900/40 transition-all hover:shadow-emerald-900/60 active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>New Scraping Run</span>
          </button>
        </div>
      </div>
    </header>
  );
};
