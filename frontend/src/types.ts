export type RecommendRequest = {
  incident_prompt: string;
  outage_type: string;
  affected_machine_functions: string[];
  top_k: number;
};

export type Citation = {
  title?: string | null;
  content?: string | null;
  filepath?: string | null;
  url?: string | null;
  chunk_id?: string | null;
};

export type RecommendResponse = {
  answer: string;
  citations: Citation[];
  debug: Record<string, unknown>;
};
