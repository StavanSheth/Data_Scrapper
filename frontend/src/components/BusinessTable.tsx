import React, { useState } from 'react';
import type { Business, PaginatedBusinesses } from '../types';
import {
  Search,
  ExternalLink,
  Phone,
  Globe,
  Star,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Info,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from 'lucide-react';

interface Props {
  data: PaginatedBusinesses;
  page: number;
  pageSize: number;
  search: string;
  sortBy: string;
  sortOrder: string;
  onPageChange: (p: number) => void;
  onPageSizeChange: (ps: number) => void;
  onSearchChange: (s: string) => void;
  onSortChange: (field: string) => void;
  onInspect: (business: Business) => void;
  loading: boolean;
}

export const BusinessTable: React.FC<Props> = ({
  data,
  page,
  pageSize,
  search,
  sortBy,
  sortOrder,
  onPageChange,
  onPageSizeChange,
  onSearchChange,
  onSortChange,
  onInspect,
  loading,
}) => {
  const [searchInput, setSearchInput] = useState(search);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearchChange(searchInput);
  };

  const renderSortIcon = (field: string) => {
    if (sortBy !== field) {
      return <ArrowUpDown className="w-3 h-3 text-slate-600 inline ml-1" />;
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="w-3 h-3 text-emerald-400 inline ml-1" />
    ) : (
      <ArrowDown className="w-3 h-3 text-emerald-400 inline ml-1" />
    );
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-xl overflow-hidden">
      {/* Table controls bar */}
      <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onBlur={() => onSearchChange(searchInput)}
            placeholder="Search business name, address, phone, category..."
            className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-3 py-2 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition-colors"
          />
        </form>

        <div className="flex items-center space-x-3 text-xs text-slate-400">
          <span>Rows per page:</span>
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="bg-slate-950 border border-slate-800 rounded-md px-2 py-1 text-slate-200 focus:outline-none focus:border-emerald-500"
          >
            <option value={10}>10</option>
            <option value={25}>25</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span className="text-slate-300 font-medium">
            Total: <span className="text-emerald-400 font-mono">{data.total}</span>
          </span>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="bg-slate-950/70 border-b border-slate-800 text-slate-400 uppercase tracking-wider font-semibold">
              <th
                onClick={() => onSortChange('name')}
                className="py-3 px-4 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <span>Business Name</span>
                {renderSortIcon('name')}
              </th>
              <th
                onClick={() => onSortChange('category')}
                className="py-3 px-4 cursor-pointer hover:text-slate-200 transition-colors"
              >
                <span>Category</span>
                {renderSortIcon('category')}
              </th>
              <th className="py-3 px-4">Address & City</th>
              <th className="py-3 px-4">Phone</th>
              <th className="py-3 px-4">Website</th>
              <th
                onClick={() => onSortChange('rating')}
                className="py-3 px-4 cursor-pointer hover:text-slate-200 transition-colors text-right"
              >
                <span>Rating</span>
                {renderSortIcon('rating')}
              </th>
              <th className="py-3 px-4 text-center">Status</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-200">
            {loading ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-400">
                  <div className="inline-block animate-spin w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full mb-2"></div>
                  <p>Loading business records...</p>
                </td>
              </tr>
            ) : data.items.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-400">
                  <p className="text-base font-medium text-slate-300">No businesses found</p>
                  <p className="text-xs text-slate-500 mt-1">
                    {search ? 'Try clearing your search query' : 'Businesses will appear here as scraping progresses'}
                  </p>
                </td>
              </tr>
            ) : (
              data.items.map((b) => (
                <tr
                  key={b.id}
                  className="hover:bg-slate-800/40 transition-colors group"
                >
                  {/* Name */}
                  <td className="py-3 px-4 font-medium text-slate-100 max-w-xs">
                    <div className="truncate font-semibold">{b.name}</div>
                    <div className="text-[10px] text-slate-400 truncate font-mono">
                      {b.normalized_name}
                    </div>
                  </td>

                  {/* Category */}
                  <td className="py-3 px-4 max-w-[150px]">
                    <span className="inline-block px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[11px] truncate">
                      {b.category || 'General'}
                    </span>
                  </td>

                  {/* Address */}
                  <td className="py-3 px-4 max-w-sm">
                    <div className="truncate text-slate-300" title={b.address || ''}>
                      {b.address || '—'}
                    </div>
                    <div className="text-[10px] text-slate-500 flex items-center space-x-1 mt-0.5">
                      <MapPin className="w-2.5 h-2.5 text-slate-400" />
                      <span>{b.city || 'Unknown city'}</span>
                    </div>
                  </td>

                  {/* Phone */}
                  <td className="py-3 px-4 whitespace-nowrap">
                    {b.normalized_phone ? (
                      <span className="font-mono text-emerald-400 flex items-center space-x-1">
                        <Phone className="w-3 h-3 text-emerald-500" />
                        <span>{b.normalized_phone}</span>
                      </span>
                    ) : b.phone ? (
                      <span className="text-slate-400 text-[11px]">{b.phone}</span>
                    ) : (
                      <span className="text-slate-600 text-[11px] italic">Missing</span>
                    )}
                  </td>

                  {/* Website */}
                  <td className="py-3 px-4 max-w-[180px] truncate">
                    {b.website_domain ? (
                      <a
                        href={b.website || `https://${b.website_domain}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-emerald-400 hover:underline flex items-center space-x-1 truncate"
                        title={b.website || ''}
                      >
                        <Globe className="w-3 h-3 flex-shrink-0" />
                        <span className="truncate">{b.website_domain}</span>
                      </a>
                    ) : (
                      <span className="text-slate-600 text-[11px] italic">Missing</span>
                    )}
                  </td>

                  {/* Rating */}
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    {b.rating ? (
                      <div>
                        <div className="flex items-center justify-end space-x-1 text-gold-400 font-semibold font-mono">
                          <Star className="w-3 h-3 fill-current text-gold-400" />
                          <span>{b.rating.toFixed(1)}</span>
                        </div>
                        {b.review_count !== undefined && b.review_count !== null && (
                          <span className="text-[10px] text-slate-500">
                            ({b.review_count} rev)
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-slate-600">—</span>
                    )}
                  </td>

                  {/* Status */}
                  <td className="py-3 px-4 text-center whitespace-nowrap">
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      {b.status}
                    </span>
                  </td>

                  {/* Actions */}
                  <td className="py-3 px-4 text-right whitespace-nowrap">
                    <div className="flex items-center justify-end space-x-2">
                      {b.google_profile_url && (
                        <a
                          href={b.google_profile_url}
                          target="_blank"
                          rel="noreferrer"
                          title="Open Google Maps listing"
                          className="p-1 rounded text-slate-400 hover:text-emerald-400 hover:bg-slate-800 transition-colors"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                      <button
                        onClick={() => onInspect(b)}
                        className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium transition-colors"
                      >
                        <Info className="w-3 h-3 text-emerald-400" />
                        <span>Inspect</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
        <div>
          Showing page <span className="font-semibold text-slate-200">{data.page}</span> of{' '}
          <span className="font-semibold text-slate-200">{data.total_pages}</span> (
          {data.total} total businesses)
        </div>

        <div className="flex items-center space-x-2">
          <button
            disabled={page <= 1 || loading}
            onClick={() => onPageChange(page - 1)}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition-colors"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
            <span>Previous</span>
          </button>
          <button
            disabled={page >= data.total_pages || loading}
            onClick={() => onPageChange(page + 1)}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-800 transition-colors"
          >
            <span>Next</span>
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  );
};
