import React, { useState } from 'react';
import type { CreateRunPayload } from './types';
import { useRuns } from './hooks/useRuns';
import { useBusinesses } from './hooks/useBusinesses';
import { useRunMonitor } from './hooks/useRunMonitor';
import { Navbar } from './components/Navbar';
import { Dashboard } from './components/Dashboard';
import { RunMonitor } from './components/RunMonitor';
import { BusinessTable } from './components/BusinessTable';
import { BusinessDetailDrawer } from './components/BusinessDetailDrawer';
import { NewRunModal } from './components/NewRunModal';
import { ArrowLeft, RefreshCw } from 'lucide-react';

export const App: React.FC = () => {
  const {
    runs,
    activeRun,
    setActiveRun,
    isHealthy,
    loadRuns,
    createNewRun,
    cancelActiveRun,
  } = useRuns();

  const {
    data: businessesData,
    page,
    setPage,
    pageSize,
    setPageSize,
    search,
    handleSearch,
    sortBy,
    sortOrder,
    handleSort,
    loading: tableLoading,
    reload: reloadBusinesses,
    inspectedBusiness,
    setInspectedBusiness,
  } = useBusinesses(activeRun?.id);

  const [isNewRunOpen, setIsNewRunOpen] = useState(false);

  // Real-time WebSocket monitoring with polling fallback
  useRunMonitor(
    activeRun,
    (updated) => {
      setActiveRun(updated);
      loadRuns();
      reloadBusinesses();
    },
    () => {
      reloadBusinesses();
    }
  );

  const handleCreateRun = async (payload: CreateRunPayload) => {
    await createNewRun(payload);
    setPage(1);
  };

  const handleCancelRun = async () => {
    if (!activeRun) return;
    await cancelActiveRun(activeRun.id);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-300">
      <Navbar
        onNewRunClick={() => {
          setActiveRun(null);
          setIsNewRunOpen(true);
        }}
        onRefresh={() => {
          loadRuns();
          reloadBusinesses();
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
                  onClick={reloadBusinesses}
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
                onSearchChange={handleSearch}
                onSortChange={handleSort}
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
