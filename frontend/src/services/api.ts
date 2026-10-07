import type { Run, Business, PaginatedBusinesses, CreateRunPayload } from '../types';

const API_BASE = 'http://127.0.0.1:8000/api';

export async function checkHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

export async function fetchRuns(): Promise<Run[]> {
  const res = await fetch(`${API_BASE}/runs?limit=50`);
  if (!res.ok) throw new Error('Failed to fetch runs');
  const data = await res.json();
  return data.runs;
}

export async function fetchRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs/${runId}`);
  if (!res.ok) throw new Error(`Failed to fetch run ${runId}`);
  return res.json();
}

export async function createRun(payload: CreateRunPayload): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to create run');
  }
  return res.json();
}

export async function startRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs/${runId}/start`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to start run ${runId}`);
  return res.json();
}

export async function cancelRun(runId: string): Promise<Run> {
  const res = await fetch(`${API_BASE}/runs/${runId}/cancel`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error(`Failed to cancel run ${runId}`);
  return res.json();
}

export async function fetchBusinesses(
  runId: string,
  page = 1,
  pageSize = 50,
  search = '',
  sortBy = 'created_at',
  sortOrder = 'desc'
): Promise<PaginatedBusinesses> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
    sort_by: sortBy,
    sort_order: sortOrder,
  });
  if (search) {
    params.set('search', search);
  }

  const res = await fetch(`${API_BASE}/runs/${runId}/businesses?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch businesses for run ${runId}`);
  return res.json();
}

export async function fetchBusiness(runId: string, businessId: string): Promise<Business> {
  const res = await fetch(`${API_BASE}/runs/${runId}/businesses/${businessId}`);
  if (!res.ok) throw new Error(`Failed to fetch business ${businessId}`);
  return res.json();
}
