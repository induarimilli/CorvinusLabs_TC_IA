/**
 * Floating scavenger-hunt guide: advances on Continue or when the user
 * navigates to the highlighted sidebar route; final step unlocks tools.
 */
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface OnboardingStep {
  id: string;
  title: string;
  content: string;
  route: string;
  highlight_nav: string | null;
  advance: 'button' | 'navigate' | 'complete';
}

interface ChecklistItem {
  id: string;
  label: string;
}

interface OnboardingStatus {
  required: boolean;
  completed: boolean;
  lab_name: string;
  current_step: OnboardingStep | null;
  checklist: ChecklistItem[];
  completed_step_ids: string[];
  steps: OnboardingStep[];
}

interface OnboardingGuideProps {
  highlightNav: string | null;
  onHighlightChange: (path: string | null) => void;
}

function renderContent(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

export default function OnboardingGuide({ onHighlightChange }: Omit<OnboardingGuideProps, 'highlightNav'>) {
  const { orgId, labId, token } = useAuth();
  const location = useLocation();
  const queryClient = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ['onboarding', orgId, labId],
    queryFn: () => api<OnboardingStatus>(
      `/organizations/${orgId}/labs/${labId}/onboarding`,
      { orgId, labId, token }
    ),
    enabled: !!orgId && !!labId && !!token,
  });

  const advanceMutation = useMutation({
    mutationFn: () => api(
      `/organizations/${orgId}/labs/${labId}/onboarding/advance`,
      { method: 'POST', orgId, labId, token }
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });

  const navigateAdvanceMutation = useMutation({
    mutationFn: (visitedPath: string) => api(
      `/organizations/${orgId}/labs/${labId}/onboarding/advance-navigate?visited_path=${encodeURIComponent(visitedPath)}`,
      { method: 'POST', orgId, labId, token }
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
    },
  });

  const completeMutation = useMutation({
    mutationFn: () => api(
      `/organizations/${orgId}/labs/${labId}/onboarding/complete`,
      { method: 'POST', orgId, labId, token }
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['me'] });
      queryClient.invalidateQueries({ queryKey: ['onboarding'] });
      queryClient.invalidateQueries({ queryKey: ['tools-catalog'] });
      onHighlightChange(null);
    },
  });

  const step = status?.current_step;
  const active = status?.required && !status.completed && step;
  const navigatedRef = useRef<string | null>(null);

  useEffect(() => {
    navigatedRef.current = null;
  }, [step?.id]);

  useEffect(() => {
    if (!active || !step) {
      onHighlightChange(null);
      return;
    }
    onHighlightChange(step.highlight_nav);
    return () => onHighlightChange(null);
  }, [active, step, onHighlightChange]);

  useEffect(() => {
    if (!active || !step || step.advance !== 'navigate' || !step.highlight_nav) return;
    if (location.pathname === step.highlight_nav && navigatedRef.current !== step.id) {
      navigatedRef.current = step.id;
      navigateAdvanceMutation.mutate(step.highlight_nav);
    }
  }, [location.pathname, active, step?.id, step?.advance, step?.highlight_nav]);

  if (!active || !step) return null;

  const onRoute = location.pathname === step.route
    || (step.route !== '/' && location.pathname.startsWith(step.route));

  if (!onRoute) return null;

  const isChecklist = step.id === 'checklist';
  const stepIndex = status.steps.findIndex(s => s.id === step.id);

  return (
    <div className="onboarding-guide">
      <div className="onboarding-guide-header">
        <span className="onboarding-guide-badge">Onboarding · {status.lab_name}</span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          Step {stepIndex + 1} of {status.steps.length}
        </span>
      </div>
      <h3>{step.title}</h3>
      <p>{renderContent(step.content)}</p>

      {isChecklist && status.checklist.length > 0 && (
        <ul className="onboarding-checklist">
          {status.checklist.map(item => (
            <li key={item.id}>
              <span className="onboarding-check">○</span>
              {item.label}
            </li>
          ))}
        </ul>
      )}

      <div className="onboarding-guide-actions">
        {step.advance === 'button' && (
          <button
            onClick={() => advanceMutation.mutate()}
            disabled={advanceMutation.isPending}
          >
            Continue
          </button>
        )}
        {step.advance === 'navigate' && (
          <span style={{ fontSize: 12, color: 'var(--accent)' }}>
            ↑ Click the highlighted item in the sidebar
          </span>
        )}
        {step.advance === 'complete' && (
          <button
            onClick={() => completeMutation.mutate()}
            disabled={completeMutation.isPending}
          >
            Finish onboarding & unlock tools
          </button>
        )}
      </div>
    </div>
  );
}
