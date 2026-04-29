import { useState } from 'react';
import { api } from './api/client';
import { IncidentForm } from './components/IncidentForm';
import { PlanSummary } from './components/PlanSummary';
import { RecoveryStepCard } from './components/RecoveryStepCard';
import type { IncidentInput, RecoveryPlan } from './types/api';
import './App.css';

export default function App() {
  const [plan, setPlan] = useState<RecoveryPlan | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());

  const handleSubmit = async (incident: IncidentInput) => {
    setIsLoading(true);
    setError('');
    setPlan(null);
    setExpandedSteps(new Set());
    try {
      const result = await api.recommend(incident);
      setPlan(result);
      setExpandedSteps(new Set(result.recovery_steps.slice(0, 3).map((s) => s.step_number)));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unexpected error. Is the backend running?');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleStep = (stepNumber: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(stepNumber)) {
        next.delete(stepNumber);
      } else {
        next.add(stepNumber);
      }
      return next;
    });
  };

  const expandAll = () => {
    if (plan) setExpandedSteps(new Set(plan.recovery_steps.map((s) => s.step_number)));
  };

  const collapseAll = () => setExpandedSteps(new Set());

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-header__inner">
          <div className="logo">
            <span className="logo-icon">🛡️</span>
            <div>
              <h1 className="app-title">PFR Recovery Advisor</h1>
              <p className="app-subtitle">PilotFish Control Plane · Dependency-Aware Recovery</p>
            </div>
          </div>
        </div>
      </header>

      <main className="app-main">
        <div className="container">
          <section className="panel panel--input">
            <h2 className="panel-title">Incident Input</h2>
            <IncidentForm onSubmit={handleSubmit} isLoading={isLoading} />
          </section>

          <section className="panel panel--output">
            <h2 className="panel-title">Recovery Plan</h2>

            {error && (
              <div className="alert alert--error" role="alert">
                <strong>Error:</strong> {error}
              </div>
            )}

            {!plan && !isLoading && !error && (
              <div className="empty-state">
                <p>Submit an incident on the left to generate a recovery plan.</p>
              </div>
            )}

            {isLoading && (
              <div className="loading-state">
                <div className="spinner spinner--large" aria-label="Generating plan…" />
                <p>Analysing dependencies and retrieving relevant documents…</p>
              </div>
            )}

            {plan && (
              <>
                <PlanSummary plan={plan} />
                <div className="steps-toolbar">
                  <span className="steps-count">{plan.recovery_steps.length} steps</span>
                  <div className="steps-toolbar__actions">
                    <button className="btn btn--ghost btn--sm" onClick={expandAll}>
                      Expand all
                    </button>
                    <button className="btn btn--ghost btn--sm" onClick={collapseAll}>
                      Collapse all
                    </button>
                  </div>
                </div>
                <div className="steps-list">
                  {plan.recovery_steps.map((step) => (
                    <RecoveryStepCard
                      key={step.step_number}
                      step={step}
                      isExpanded={expandedSteps.has(step.step_number)}
                      onToggle={() => toggleStep(step.step_number)}
                    />
                  ))}
                </div>
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}
