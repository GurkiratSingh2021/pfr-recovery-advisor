import type { RecoveryStep } from '../types/api';

interface Props {
  step: RecoveryStep;
  isExpanded: boolean;
  onToggle: () => void;
}

export function RecoveryStepCard({ step, isExpanded, onToggle }: Props) {
  return (
    <div className={`step-card ${step.is_gated ? 'step-card--gated' : ''}`}>
      {/* Header */}
      <button className="step-card__header" onClick={onToggle} aria-expanded={isExpanded}>
        <span className="step-number">Step {step.step_number}</span>
        <span className="step-service">{step.target_service}</span>
        {step.is_gated && <span className="badge badge--gated">Gated</span>}
        <span className="step-toggle">{isExpanded ? '▲' : '▼'}</span>
      </button>

      {isExpanded && (
        <div className="step-card__body">
          {/* Action */}
          <section className="step-section">
            <h4>Action</h4>
            <p>{step.action}</p>
          </section>

          {/* Why Now */}
          <section className="step-section">
            <h4>Why this order?</h4>
            <p className="why-now">{step.why_now}</p>
          </section>

          {/* Validations */}
          {step.validations.length > 0 && (
            <section className="step-section">
              <h4>Validations</h4>
              <ul>
                {step.validations.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </section>
          )}

          {/* Expected Signal */}
          <section className="step-section">
            <h4>Expected signal</h4>
            <code className="signal-text">{step.expected_signal}</code>
          </section>

          {/* Rollback */}
          {step.rollback && (
            <section className="step-section step-section--rollback">
              <h4>🔄 Rollback</h4>
              <p>{step.rollback}</p>
            </section>
          )}

          {/* Citations */}
          {step.citations.length > 0 && (
            <section className="step-section step-section--citations">
              <h4>📄 Evidence ({step.citations.length})</h4>
              <ul className="citation-list">
                {step.citations.map((c, idx) => (
                  <li key={`${c.doc_id}-${idx}`} className="citation-item">
                    <span className="citation-title">{c.title}</span>
                    <span className="citation-type badge">{c.doc_type}</span>
                    <span className="citation-score">
                      {Math.round(c.relevance_score * 100)}% match
                    </span>
                    <p className="citation-excerpt">{c.excerpt}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
