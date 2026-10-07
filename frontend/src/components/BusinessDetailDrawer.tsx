import React, { useEffect, useState } from 'react';
import type { Business } from '../types';
import { fetchBusiness } from '../services/api';
import {
  X,
  MapPin,
  Phone,
  Globe,
  Star,
  ExternalLink,
  ShieldCheck,
  Clock,
  Layers,
} from 'lucide-react';

interface Props {
  business: Business | null;
  onClose: () => void;
}

export const BusinessDetailDrawer: React.FC<Props> = ({ business: initialBusiness, onClose }) => {
  const [business, setBusiness] = useState<Business | null>(initialBusiness);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setBusiness(initialBusiness);
    if (initialBusiness && (!initialBusiness.provenances || initialBusiness.provenances.length === 0)) {
      setLoading(true);
      fetchBusiness(initialBusiness.run_id, initialBusiness.id)
        .then((full) => setBusiness(full))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [initialBusiness]);

  if (!business) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/60 backdrop-blur-sm flex justify-end animate-in fade-in duration-150">
      <div className="w-full max-w-2xl bg-slate-900 border-l border-slate-800 h-full shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-slate-800 flex items-start justify-between bg-slate-950/60">
          <div>
            <div className="flex items-center space-x-2 mb-1">
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                {business.source} Source
              </span>
              <span className="text-xs text-slate-500 font-mono">ID: {business.id}</span>
            </div>
            <h2 className="text-xl font-bold text-slate-100">{business.name}</h2>
            <p className="text-xs text-slate-400 font-mono mt-0.5">
              Normalized: {business.normalized_name}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-xs text-slate-300">
          {/* Quick Metrics */}
          <div className="grid grid-cols-3 gap-3">
            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-500 mb-1 flex items-center space-x-1">
                <Star className="w-3.5 h-3.5 text-gold-400" />
                <span>Rating</span>
              </div>
              <div className="text-lg font-bold font-mono text-slate-100">
                {business.rating ? `${business.rating.toFixed(1)} / 5.0` : '—'}
              </div>
              <div className="text-[10px] text-slate-500">
                {business.review_count !== undefined ? `${business.review_count} reviews` : 'No reviews'}
              </div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-500 mb-1 flex items-center space-x-1">
                <Layers className="w-3.5 h-3.5 text-emerald-400" />
                <span>Category</span>
              </div>
              <div className="text-sm font-semibold text-slate-100 truncate">
                {business.category || 'General'}
              </div>
              <div className="text-[10px] text-slate-500">Google primary</div>
            </div>

            <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
              <div className="text-slate-500 mb-1 flex items-center space-x-1">
                <Clock className="w-3.5 h-3.5 text-slate-400" />
                <span>Hours</span>
              </div>
              <div className="text-xs font-medium text-slate-200 truncate">
                {business.opening_hours || 'Not specified'}
              </div>
              <div className="text-[10px] text-slate-500">Operating status</div>
            </div>
          </div>

          {/* Contact Details */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <Phone className="w-3.5 h-3.5 text-emerald-400" />
              <span>Contact Channels</span>
            </h3>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <span className="text-slate-500 block text-[11px]">Normalized Phone</span>
                <span className="font-mono text-emerald-400 font-medium">
                  {business.normalized_phone || <span className="text-slate-600 italic">None</span>}
                </span>
                {business.phone && business.phone !== business.normalized_phone && (
                  <span className="block text-[10px] text-slate-500">Raw: {business.phone}</span>
                )}
              </div>

              <div>
                <span className="text-slate-500 block text-[11px]">Website</span>
                {business.website ? (
                  <a
                    href={business.website}
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline flex items-center space-x-1 truncate"
                  >
                    <Globe className="w-3 h-3 flex-shrink-0" />
                    <span className="truncate">{business.website_domain || business.website}</span>
                  </a>
                ) : (
                  <span className="text-slate-600 italic">No website found</span>
                )}
              </div>
            </div>
          </div>

          {/* Location Details */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-400" />
              <span>Location & Geospatial</span>
            </h3>

            <p className="text-slate-200 text-xs">{business.address || 'Address unavailable'}</p>

            <div className="grid grid-cols-3 gap-2 pt-2 text-[11px] border-t border-slate-900">
              <div>
                <span className="text-slate-500 block">City</span>
                <span className="text-slate-200 font-medium">{business.city || '—'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">PIN / Postal</span>
                <span className="text-slate-200 font-medium">{business.postal_code || '—'}</span>
              </div>
              <div>
                <span className="text-slate-500 block">State</span>
                <span className="text-slate-200 font-medium">{business.state || '—'}</span>
              </div>
            </div>

            {business.latitude && business.longitude && (
              <div className="pt-2 text-[11px] font-mono text-slate-400 flex items-center space-x-3">
                <span>Lat: {business.latitude}</span>
                <span>Lng: {business.longitude}</span>
              </div>
            )}
          </div>

          {/* Provenance Audit Table */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>Field Provenance & Lineage</span>
              </h3>
              <span className="text-[10px] text-slate-500">
                {business.provenances?.length || 0} signals
              </span>
            </div>

            {loading ? (
              <p className="text-slate-500 text-center py-4">Loading provenance records...</p>
            ) : business.provenances && business.provenances.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-[11px]">
                  <thead>
                    <tr className="text-slate-500 border-b border-slate-800">
                      <th className="py-1.5 pr-2">Field</th>
                      <th className="py-1.5 px-2">Method</th>
                      <th className="py-1.5 px-2">Value</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900">
                    {business.provenances.map((p) => (
                      <tr key={p.id} className="text-slate-300">
                        <td className="py-1.5 pr-2 font-mono text-emerald-400">{p.field_name}</td>
                        <td className="py-1.5 px-2 text-slate-400">{p.extraction_method || 'direct'}</td>
                        <td className="py-1.5 px-2 max-w-xs truncate" title={p.field_value || ''}>
                          {p.field_value}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-slate-500 italic py-2">No provenance records available.</p>
            )}
          </div>

          {/* External links */}
          {business.google_profile_url && (
            <div className="pt-2">
              <a
                href={business.google_profile_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center space-x-2 text-xs font-medium text-emerald-400 hover:text-emerald-300 transition-colors"
              >
                <span>Open Google Maps Place Profile</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
