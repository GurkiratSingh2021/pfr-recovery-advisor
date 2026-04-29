/**
 * TypeScript types mirroring the Pydantic schemas from the backend.
 * Keep in sync with backend/app/models/schemas.py.
 */

export interface IncidentInput {
  incident_id?: string;
  title?: string;
  description: string;
  impacted_services?: string[];
  observed_signals?: Record<string, string>;
  region?: string;
  severity?: number;
}

export interface Citation {
  doc_id: string;
  title: string;
  doc_type: string;
  excerpt: string;
  relevance_score: number;
}

export interface RecoveryStep {
  step_number: number;
  target_service: string;
  action: string;
  why_now: string;
  expected_signal: string;
  validations: string[];
  rollback: string;
  citations: Citation[];
  is_gated: boolean;
}

export interface SafetyCheck {
  check: string;
  passed: boolean;
  reason?: string;
}

export interface RecoveryPlan {
  incident_id: string;
  incident_summary: string;
  detected_services: string[];
  recovery_steps: RecoveryStep[];
  safety_checks: SafetyCheck[];
  open_questions: string[];
  confidence: number;
  planner_version: string;
}

export interface IngestRequest {
  content: string;
  doc_id: string;
  title?: string;
  doc_type?: string;
  service?: string;
  source_path?: string;
}

export interface IngestResponse {
  doc_id: string;
  chunks_stored: number;
  message: string;
}
