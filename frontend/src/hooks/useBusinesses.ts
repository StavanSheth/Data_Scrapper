import { useState, useEffect, useCallback } from 'react';
import type { Business, PaginatedBusinesses } from '../types';
import { fetchBusinesses } from '../services/api';

export function useBusinesses(activeRunId?: string) {
  const [data, setData] = useState<PaginatedBusinesses>({
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
  const [loading, setLoading] = useState(false);
  const [inspectedBusiness, setInspectedBusiness] = useState<Business | null>(null);

  const load = useCallback(async () => {
    if (!activeRunId) return;
    try {
      setLoading(true);
      const res = await fetchBusinesses(activeRunId, page, pageSize, search, sortBy, sortOrder);
      setData(res);
    } catch (err) {
      console.error('Failed to load businesses:', err);
    } finally {
      setLoading(false);
    }
  }, [activeRunId, page, pageSize, search, sortBy, sortOrder]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
    setPage(1);
  };

  const handleSearch = (term: string) => {
    setSearch(term);
    setPage(1);
  };

  return {
    data,
    page,
    setPage,
    pageSize,
    setPageSize,
    search,
    handleSearch,
    sortBy,
    sortOrder,
    handleSort,
    loading,
    reload: load,
    inspectedBusiness,
    setInspectedBusiness,
  };
}
