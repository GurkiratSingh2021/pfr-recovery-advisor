import type { RecoveryPlan } from '../types/api';
import type { SafetyCheck } from '../types/api';

interface Props {
  plan: RecoveryPlan;
}

function SafetyCheckRow({ check }: { check: SafetyCheck }) {
  return (
    <li className={`safety-check ${check.passed ? 'safety-check--pass' : 'safety-check--fail'}`}>
      <span className="safety-icon">{check.passed ? '✅' : '❌'}</span>
      <span className="safety-name">{check.check}</span>
      {!check.passed && check.reason && (
        <span className="safety-reason"> — {check.reason}</span>
      )}
    </li>
  );
}

export function PlanSummary({ plan }: Props) {
  const confidencePct = Math.round(plan.confidence * 100);
  const confidenceClass =
    plan.confidence >= 0.8 ? 'high' : plan.confidence >= 0.5 ? 'medium' : 'low';

  return (
    <div className="plan-summary">
      <div className="plan-summary__header">
        <div>
          <h2 className="plan-title">{plan.incident_summary}</h2>
          <p className="plan-meta">
            Incident <strong>{plan.incident_id}</strong> · {plan.detected_services.length} service(s)
            affected · planner: <code>{plan.planner_version}</code>
          </p>
        </div>
        <div className={`confidence-badge confidence-badge--${confidenceClass}`}>
          <span className="confidence-value">{confidencePct}%</span>
          <span className="confidence-label">confidence</span>
        </div>
      </div>

      {/* Detected services */}
      <div className="detected-services">
        <strong>Detected services:</strong>
        {plan.detected_services.map((s) => (
          <span key={s} className="service-tag">{s}</span>
        ))}
      </div>

      {/* Safety checks */}
      {plan.safety_checks.length > 0 && (
        <div className="safety-checks">
          <strong>Safety checks:</strong>
          <ul>
            {plan.safety_checks.map((c, i) => (
              <SafetyCheckRow key={i} check={c} />
            ))}
          </ul>
        </div>
      )}

      {/* Open questions */}
      {plan.open_questions.length > 0 && (
        <div className="open-questions">
          <strong>⚠️ Open questions:</strong>
          <ul>
            {plan.open_questions.map((q, i) => (
              <li key={i}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
