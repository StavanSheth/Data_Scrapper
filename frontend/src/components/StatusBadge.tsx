import React from 'react';
import type { RunStatus } from '../types';

interface Props {
  status: RunStatus | string;
}

export const StatusBadge: React.FC<Props> = ({ status }) => {
  const getStyle = () => {
    switch (status) {
      case 'RUNNING':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 animate-pulse';
      case 'COMPLETED':
        return 'bg-green-500/10 text-green-400 border-green-500/30';
      case 'PARTIAL':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      case 'FAILED':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'CANCELLED':
        return 'bg-slate-500/10 text-slate-400 border-slate-500/30';
      case 'QUEUED':
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
      default:
        return 'bg-slate-500/10 text-slate-400 border-slate-500/20';
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStyle()}`}
    >
      <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-current"></span>
      {status}
    </span>
  );
};
