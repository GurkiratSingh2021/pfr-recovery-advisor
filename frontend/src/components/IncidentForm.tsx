import { useState } from 'react';
import type { IncidentInput } from '../types/api';

const SAMPLE_INCIDENT: IncidentInput = {
  incident_id: 'ICM-20240315-001',
  title: 'Control Plane API degraded – auth failures + high 5xx',
  description:
    'Starting at 14:18 UTC, customers reported inability to create or update DM resources. API telemetry shows 42% 5xx rate on POST /resources. Auth middleware is logging "token validation failed" errors. Config service health probe is returning 503.',
  impacted_services: ['PilotFish.ControlPlane.API', 'PilotFish.Config'],
  observed_signals: {
    'SLO:5xx_rate': '42%',
    'SLO:latency_p99': '8200ms',
    'ICM:auth_failures': 'elevated',
    'SLO:config_fetch_success_rate': '12%',
  },
  region: 'eastus2',
  severity: 2,
};

interface Props {
  onSubmit: (incident: IncidentInput) => void;
  isLoading: boolean;
}

export function IncidentForm({ onSubmit, isLoading }: Props) {
  const [rawJson, setRawJson] = useState(JSON.stringify(SAMPLE_INCIDENT, null, 2));
  const [parseError, setParseError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setParseError('');
    try {
      const parsed = JSON.parse(rawJson) as IncidentInput;
      if (!parsed.description) {
        setParseError('JSON must include a "description" field.');
        return;
      }
      onSubmit(parsed);
    } catch {
      setParseError('Invalid JSON – please fix the syntax and try again.');
    }
  };

  const handleLoadSample = () => {
    setRawJson(JSON.stringify(SAMPLE_INCIDENT, null, 2));
    setParseError('');
  };

  return (
    <form className="incident-form" onSubmit={handleSubmit}>
      <div className="form-header">
        <label htmlFor="incident-input" className="form-label">
          Paste incident JSON or free-text description
        </label>
        <button type="button" className="btn btn--secondary btn--sm" onClick={handleLoadSample}>
          Load sample
        </button>
      </div>
      <textarea
        id="incident-input"
        className={`incident-textarea ${parseError ? 'incident-textarea--error' : ''}`}
        value={rawJson}
        onChange={(e) => setRawJson(e.target.value)}
        rows={16}
        spellCheck={false}
        placeholder='{"description": "Paste your incident details here..."}'
      />
      {parseError && <p className="form-error">{parseError}</p>}
      <div className="form-actions">
        <button type="submit" className="btn btn--primary" disabled={isLoading}>
          {isLoading ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Generating plan…
            </>
          ) : (
            '⚡ Get Recovery Plan'
          )}
        </button>
      </div>
    </form>
  );
}
