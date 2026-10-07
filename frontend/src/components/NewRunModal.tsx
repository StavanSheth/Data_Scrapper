import React, { useState } from 'react';
import { X, Play, MapPin, Tag, Hash, Sliders } from 'lucide-react';
import type { CreateRunPayload } from '../types';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: CreateRunPayload) => Promise<void>;
}

const CITY_SUGGESTIONS = ['Mumbai', 'Delhi', 'Bengaluru', 'Pune', 'Hyderabad'];
const CATEGORY_SUGGESTIONS = ['Salon', 'Spa', 'Restaurant', 'Cafe', 'Car Garage', 'Dental Clinic'];
const LIMIT_OPTIONS = [10, 25, 50, 100, 250, 500];

export const NewRunModal: React.FC<Props> = ({ isOpen, onClose, onSubmit }) => {
  const [city, setCity] = useState('Mumbai');
  const [category, setCategory] = useState('Salon');
  const [limit, setLimit] = useState(10);
  const [threshold, setThreshold] = useState(80);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!city.trim()) {
      setError('City name is required.');
      return;
    }
    if (!category.trim()) {
      setError('Business category is required.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await onSubmit({
        city: city.trim(),
        category: category.trim(),
        limit,
        confidence_threshold: threshold / 100,
        start_immediately: true,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to start scraping run');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full shadow-2xl overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">Configure New Scraping Run</h2>
            <p className="text-xs text-slate-400 mt-0.5">Google Maps Discovery & Entity Normalization</p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
              {error}
            </div>
          )}

          {/* City */}
          <div>
            <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
              <MapPin className="w-3.5 h-3.5 text-emerald-400" />
              <span>Target City</span>
            </label>
            <input
              type="text"
              value={city}
              onChange={(e) => setCity(e.target.value)}
              placeholder="e.g. Mumbai"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {CITY_SUGGESTIONS.map((c) => (
                <button
                  type="button"
                  key={c}
                  onClick={() => setCity(c)}
                  className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                    city === c
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Category */}
          <div>
            <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
              <Tag className="w-3.5 h-3.5 text-emerald-400" />
              <span>Business Category</span>
            </label>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="e.g. Salon"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3.5 py-2.5 text-slate-100 text-sm focus:outline-none focus:border-emerald-500 transition-colors"
            />
            <div className="flex flex-wrap gap-1.5 mt-2">
              {CATEGORY_SUGGESTIONS.map((cat) => (
                <button
                  type="button"
                  key={cat}
                  onClick={() => setCategory(cat)}
                  className={`text-xs px-2 py-0.5 rounded border transition-colors ${
                    category === cat
                      ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40'
                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {cat}
                </button>
              ))}
            </div>
          </div>

          {/* Limit */}
          <div>
            <label className="block text-xs font-medium text-slate-300 uppercase tracking-wider mb-1.5 flex items-center space-x-1.5">
              <Hash className="w-3.5 h-3.5 text-emerald-400" />
              <span>Maximum Businesses to Scrape</span>
            </label>
            <div className="grid grid-cols-6 gap-1.5">
              {LIMIT_OPTIONS.map((opt) => (
                <button
                  type="button"
                  key={opt}
                  onClick={() => setLimit(opt)}
                  className={`py-2 text-xs font-medium rounded-lg border text-center transition-colors ${
                    limit === opt
                      ? 'bg-emerald-600/30 text-emerald-300 border-emerald-500'
                      : 'bg-slate-950 text-slate-400 border-slate-800 hover:text-slate-200'
                  }`}
                >
                  {opt}
                </button>
              ))}
            </div>
          </div>

          {/* Advanced / Future Slice Configuration */}
          <div className="pt-2 border-t border-slate-800/60">
            <details className="group">
              <summary className="text-xs text-slate-400 hover:text-slate-200 cursor-pointer flex items-center justify-between py-1 list-none">
                <span className="flex items-center space-x-1.5 font-medium">
                  <Sliders className="w-3.5 h-3.5 text-slate-400 group-hover:text-emerald-400 transition-colors" />
                  <span>Advanced Settings</span>
                  <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">Slice 2+</span>
                </span>
                <span className="text-[11px] text-slate-500 group-open:hidden">Match threshold: {threshold}%</span>
              </summary>
              <div className="mt-3 space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-medium text-slate-300">
                    Entity Match Threshold
                  </label>
                  <span className="text-xs font-bold text-emerald-400 font-mono">{threshold}%</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="95"
                  step="5"
                  value={threshold}
                  onChange={(e) => setThreshold(Number(e.target.value))}
                  className="w-full accent-emerald-500 bg-slate-950 rounded-lg cursor-pointer h-2"
                />
                <p className="text-[11px] text-slate-500">
                  Pre-configured threshold for cross-platform entity matching in Slice 2. In Slice 1, all discovered records are preserved in canonical storage.
                </p>
              </div>
            </details>
          </div>

          {/* Buttons */}
          <div className="pt-2 flex items-center justify-end space-x-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white font-medium text-sm shadow-sm transition-all shadow-emerald-900/30"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{loading ? 'Launching...' : 'Start Scraping'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
