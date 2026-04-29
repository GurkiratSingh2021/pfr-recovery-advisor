/**
 * API service layer – all calls to the FastAPI backend go through here.
 * Update VITE_API_BASE_URL in your .env (defaults to http://localhost:8000).
 */

import type { IncidentInput, IngestRequest, IngestResponse, RecoveryPlan } from '../types/api';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const errorBody = await res.text();
    throw new Error(`API error ${res.status}: ${errorBody}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** GET /api/health – liveness check. */
  health: () => request<{ status: string; version: string }>('/api/health'),

  /**
   * POST /api/recommend – submit an incident and get a dependency-aware
   * recovery plan back.
   */
  recommend: (incident: IncidentInput) =>
    request<RecoveryPlan>('/api/recommend', {
      method: 'POST',
      body: JSON.stringify(incident),
    }),

  /**
   * POST /api/ingest – add a document to the local knowledge store.
   */
  ingest: (payload: IngestRequest) =>
    request<IngestResponse>('/api/ingest', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};
