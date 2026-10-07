import React, { useState, useEffect, useCallback, useRef } from 'react';
import type { Run, Business, PaginatedBusinesses, CreateRunPayload } from './types';
import {
  fetchRuns,
  fetchRun,
  createRun,
  cancelRun,
  fetchBusinesses,
  checkHealth,
} from './services/api';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { RunMonitor } from './components/RunMonitor';
import { BusinessTable } from './components/BusinessTable';
import { BusinessDetailDrawer } from './components/BusinessDetailDrawer';
import { NewRunModal } from './components/NewRunModal';
import { ArrowLeft, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const [runs, setRuns] = useState<Run[]>([]);
  const [activeRun, setActiveRun] = useState<Run | null>(null);
  const [businessesData, setBusinessesData] = useState<PaginatedBusinesses>({
    items: [],
    page: 1,
    page_size: 50,
    total: 0,
    total_pages: 1,
  });

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const [inspectedBusiness, setInspectedBusiness] = useState<Business | null>(null);
  const [isNewRunOpen, setIsNewRunOpen] = useState(false);
  const [isHealthy, setIsHealthy] = useState(false);
  const [tableLoading, setTableLoading] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);

  // Health check on load and interval
  useEffect(() => {
    const pingHealth = () => {
      checkHealth()
        .then(() => setIsHealthy(true))
        .catch(() => setIsHealthy(false));
    };
    pingHealth();
    const interval = setInterval(pingHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Fetch runs
  const loadRuns = useCallback(async () => {
    try {
      const data = await fetchRuns();
      setRuns(data);
    } catch (e) {
      console.error('Error fetching runs:', e);
    }
  }, []);

  useEffect(() => {
    loadRuns();
  }, [loadRuns]);

  // Fetch businesses for active run
  const loadBusinesses = useCallback(async () => {
    if (!activeRun) return;
    try {
      setTableLoading(true);
      const res = await fetchBusinesses(
        activeRun.id,
        page,
        pageSize,
        search,
        sortBy,
        sortOrder
      );
      setBusinessesData(res);
    } catch (e) {
      console.error('Error fetching businesses:', e);
    } finally {
      setTableLoading(false);
    }
  }, [activeRun, page, pageSize, search, sortBy, sortOrder]);

  useEffect(() => {
    if (activeRun) {
      loadBusinesses();
    }
  }, [activeRun, loadBusinesses]);

  // WebSocket or polling for active run progress
  useEffect(() => {
    if (!activeRun) return;

    // Connect WebSocket
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
          setActiveRun((prev) => (prev ? { ...prev, ...msg } : prev));
          // Refresh runs list and table when progress updates
          loadRuns();
          loadBusinesses();
        }
      } catch (err) {
        console.error('WebSocket parse error:', err);
      }
    };

    ws.onerror = () => {
      // WS error: polling fallback handles it below
    };

    // Polling fallback every 3 seconds if run is active
    const pollInterval = setInterval(async () => {
      if (['RUNNING', 'QUEUED'].includes(activeRun.status)) {
        try {
          const fresh = await fetchRun(activeRun.id);
          setActiveRun(fresh);
          loadBusinesses();
          loadRuns();
        } catch {
          // Ignore polling errors
        }
      }
    }, 3000);

    return () => {
      ws.close();
      clearInterval(pollInterval);
    };
  }, [activeRun?.id, activeRun?.status, loadBusinesses, loadRuns]);

  // Handlers
  const handleCreateRun = async (payload: CreateRunPayload) => {
    const newRun = await createRun(payload);
    await loadRuns();
    setActiveRun(newRun);
    setPage(1);
    setSearch('');
  };

  const handleCancelRun = async () => {
    if (!activeRun) return;
    await cancelRun(activeRun.id);
    const fresh = await fetchRun(activeRun.id);
    setActiveRun(fresh);
    await loadRuns();
  };

  const handleSortChange = (field: string) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Navbar
        onNewRunClick={() => setIsNewRunOpen(true)}
        onRefresh={() => {
          loadRuns();
          if (activeRun) loadBusinesses();
        }}
        onDashboardClick={() => setActiveRun(null)}
        isHealthy={isHealthy}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeRun ? (
          <div>
            {/* Back button */}
            <div className="mb-4">
              <button
                onClick={() => setActiveRun(null)}
                className="inline-flex items-center space-x-2 text-xs font-semibold text-slate-400 hover:text-slate-100 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Back to Runs Dashboard</span>
              </button>
            </div>

            {/* Run monitor */}
            <RunMonitor
              run={activeRun}
              onCancel={handleCancelRun}
              onViewResults={() => {
                const el = document.getElementById('businesses-section');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }}
            />

            {/* Businesses table */}
            <div id="businesses-section" className="mt-8">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-base font-semibold text-slate-100">
                  Discovered & Normalized Businesses
                </h3>
                <button
                  onClick={loadBusinesses}
                  className="flex items-center space-x-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
                >
                  <RefreshCw className="w-3.5 h-3.5" />
                  <span>Refresh Results</span>
                </button>
              </div>

              <BusinessTable
                data={businessesData}
                page={page}
                pageSize={pageSize}
                search={search}
                sortBy={sortBy}
                sortOrder={sortOrder}
                onPageChange={(p) => setPage(p)}
                onPageSizeChange={(ps) => {
                  setPageSize(ps);
                  setPage(1);
                }}
                onSearchChange={(s) => {
                  setSearch(s);
                  setPage(1);
                }}
                onSortChange={handleSortChange}
                onInspect={(b) => setInspectedBusiness(b)}
                loading={tableLoading}
              />
            </div>
          </div>
        ) : (
          <Dashboard
            runs={runs}
            onSelectRun={(run) => {
              setActiveRun(run);
              setPage(1);
              setSearch('');
            }}
            onNewRunClick={() => setIsNewRunOpen(true)}
          />
        )}
      </main>

      {/* Business inspection drawer */}
      <BusinessDetailDrawer
        business={inspectedBusiness}
        onClose={() => setInspectedBusiness(null)}
      />

      {/* New Run Modal */}
      <NewRunModal
        isOpen={isNewRunOpen}
        onClose={() => setIsNewRunOpen(false)}
        onSubmit={handleCreateRun}
      />

      {/* Footer */}
      <footer className="border-t border-slate-900 py-6 text-center text-xs text-slate-600">
        <p>Mavon Intelligence Scraper • Slice 1 Google Maps Production Vertical</p>
      </footer>
    </div>
  );
};

export default App;
