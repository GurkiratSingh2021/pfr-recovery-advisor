import { useMemo, useState } from 'react';
import { getRecommendation } from './api';
import type { RecommendResponse } from './types';

const buttonStyle = (active: boolean): React.CSSProperties => ({
  borderRadius: 9999,
  border: '1px solid #cbd5e1',
  background: active ? '#0f172a' : 'white',
  color: active ? 'white' : '#0f172a',
  padding: '8px 14px',
  cursor: 'pointer'
});

const cardStyle: React.CSSProperties = {
  background: 'white',
  border: '1px solid #e2e8f0',
  borderRadius: 20,
  padding: 20,
  boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
};

export default function App() {
  const [incidentPrompt, setIncidentPrompt] = useState('DM data loss after destructive outage. Need recommended recovery order.');
  const [outageType, setOutageType] = useState('Data Loss');
  const [affectedInput, setAffectedInput] = useState('DM, SEC');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecommendResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const affected = useMemo(
    () => affectedInput.split(',').map((x) => x.trim().toUpperCase()).filter(Boolean),
    [affectedInput]
  );

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const response = await getRecommendation({
        incident_prompt: incidentPrompt,
        outage_type: outageType,
        affected_machine_functions: affected,
        top_k: 5,
      });
      setResult(response);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc', color: '#0f172a', fontFamily: 'Inter, Arial, sans-serif', padding: 24 }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', display: 'grid', gap: 24 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 24 }}>
          <div style={cardStyle}>
            <h1 style={{ marginTop: 0 }}>PFR Recovery Advisor</h1>
            <p style={{ color: '#475569' }}>Starter frontend wired to a FastAPI backend that uses Azure AI Search + Azure OpenAI.</p>

            <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>Incident prompt</label>
            <textarea
              value={incidentPrompt}
              onChange={(e) => setIncidentPrompt(e.target.value)}
              style={{ width: '100%', minHeight: 120, borderRadius: 16, border: '1px solid #cbd5e1', padding: 12, boxSizing: 'border-box' }}
            />

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 16 }}>
              <div>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>Outage type</label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                  {['Data Loss', 'Hardware Failure', 'Service Loss', 'Power Outage'].map((type) => (
                    <button key={type} onClick={() => setOutageType(type)} style={buttonStyle(outageType === type)}>{type}</button>
                  ))}
                </div>
              </div>
              <div>
                <label style={{ display: 'block', fontWeight: 600, marginBottom: 8 }}>Affected machine functions</label>
                <input
                  value={affectedInput}
                  onChange={(e) => setAffectedInput(e.target.value)}
                  placeholder="DM, SEC, ZKM"
                  style={{ width: '100%', borderRadius: 16, border: '1px solid #cbd5e1', padding: 12, boxSizing: 'border-box' }}
                />
              </div>
            </div>

            <div style={{ marginTop: 16 }}>
              <button onClick={run} disabled={loading} style={{ ...buttonStyle(true), borderRadius: 14 }}>
                {loading ? 'Running...' : 'Get recommendation'}
              </button>
            </div>
          </div>

          <div style={cardStyle}>
            <h2 style={{ marginTop: 0 }}>Repo handoff</h2>
            <ul style={{ color: '#334155', lineHeight: 1.7 }}>
              <li><code>/api/ingest</code> for uploading TSG/RCA/drill content</li>
              <li><code>/api/recommend</code> for grounded recovery recommendations</li>
              <li>Azure AI Search vector + semantic retrieval</li>
              <li>Azure OpenAI grounded chat completions with citations</li>
              <li>Simple React operator console</li>
            </ul>
          </div>
        </div>

        {error && <div style={{ ...cardStyle, borderColor: '#fecaca', background: '#fef2f2', color: '#991b1b' }}>{error}</div>}

        {result && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 0.8fr', gap: 24 }}>
            <div style={cardStyle}>
              <h2 style={{ marginTop: 0 }}>Recommendation</h2>
              <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>{result.answer}</div>
            </div>

            <div style={cardStyle}>
              <h2 style={{ marginTop: 0 }}>Citations</h2>
              {result.citations.length === 0 && <div style={{ color: '#64748b' }}>No citations returned.</div>}
              <div style={{ display: 'grid', gap: 12 }}>
                {result.citations.map((c, i) => (
                  <div key={i} style={{ border: '1px solid #e2e8f0', borderRadius: 16, padding: 12 }}>
                    <div style={{ fontWeight: 700 }}>{c.title || `Evidence ${i + 1}`}</div>
                    {c.url && <div style={{ fontSize: 12, color: '#2563eb', wordBreak: 'break-all' }}>{c.url}</div>}
                    {c.content && <div style={{ marginTop: 8, color: '#475569', fontSize: 14 }}>{c.content}</div>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
