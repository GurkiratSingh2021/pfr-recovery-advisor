import type { RecommendRequest, RecommendResponse } from './types';

export async function getRecommendation(payload: RecommendRequest): Promise<RecommendResponse> {
  const response = await fetch('/api/recommend', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || 'Request failed');
  }

  return response.json();
}
