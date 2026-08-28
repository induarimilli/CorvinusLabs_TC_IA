/**
 * App chrome: role-based nav, org/lab switcher, role-change banner,
 * and scavenger-hunt OnboardingGuide while contributor onboarding is pending.
 */
import { Link, useLocation, Navigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import OrgLabSwitcher from './OrgLabSwitcher';
import OnboardingGuide from '../onboarding/OnboardingGuide';

interface MeResponse {
  memberships: { organization_id: string; org_role: string }[];
  lab_memberships: { lab_id: string; organization_id: string; lab_role: string }[];
  is_staff: boolean;
  pending_onboarding: { lab_id: string; organization_id: string; lab_name: string }[];
  role_change_notices: { lab_id: string; organization_id: string; lab_name: string; message: string }[];
}

function effectiveRole(orgRole: string, labId: string | null, labMemberships: MeResponse['lab_memberships'], orgId: string | null): string {
  if (orgRole === 'ADMIN') return 'Admin';
  const lm = labMemberships.find(l => l.organization_id === orgId && l.lab_id === labId);
  if (lm?.lab_role === 'MANAGER') return 'Manager';
  if (lm?.lab_role === 'CONTRIBUTOR') return 'Contributor';
  const anyInOrg = labMemberships.find(l => l.organization_id === orgId);
  if (anyInOrg?.lab_role === 'MANAGER') return 'Manager';
  if (anyInOrg?.lab_role === 'CONTRIBUTOR') return 'Contributor';
  return 'Member';
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { user, logout, orgId, labId, isStaff, token, setLabId } = useAuth();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [highlightNav, setHighlightNav] = useState<string | null>(null);

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<MeResponse>('/auth/me'),
  });

  const dismissMutation = useMutation({
    mutationFn: (targetLabId: string) => api(
      `/organizations/${orgId}/labs/${targetLabId}/membership/dismiss-role-notice`,
      { method: 'POST', orgId, labId: targetLabId, token }
    ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['me'] }),
  });

  const pendingForContext = me?.pending_onboarding?.find(
    p => p.organization_id === orgId && (!labId || p.lab_id === labId)
  ) || me?.pending_onboarding?.find(p => p.organization_id === orgId);

  const hasPendingOnboarding = !isStaff && !!pendingForContext;

  useEffect(() => {
    if (pendingForContext && labId !== pendingForContext.lab_id) {
      setLabId(pendingForContext.lab_id);
    }
  }, [pendingForContext, labId, setLabId]);

  if (isStaff && !location.pathname.startsWith('/platform')) {
    return <Navigate to="/platform" replace />;
  }

  if (!isStaff && !orgId && location.pathname !== '/login') {
    return <Navigate to="/login" replace />;
  }

  const orgMembership = me?.memberships.find(m => m.organization_id === orgId);
  const orgRole = orgMembership?.org_role || '';
  const roleName = effectiveRole(orgRole, labId, me?.lab_memberships || [], orgId);

  const roleNotice = me?.role_change_notices?.find(
    n => n.organization_id === orgId && (!labId || n.lab_id === labId)
  );

  const staffNav = [
    { path: '/platform', label: 'Analytics' },
    { path: '/platform/orgs', label: 'Organizations' },
  ];

  const orgNav = [
    { path: '/', label: 'Dashboard' },
    { path: '/tasks', label: 'Tasks' },
    ...(roleName === 'Manager' ? [{ path: '/team', label: 'Team' }] : []),
    ...(roleName === 'Contributor' ? [
      { path: '/tools', label: 'App Launcher' },
      { path: '/team', label: 'Team' },
    ] : []),
    ...(roleName === 'Admin' ? [
      { path: '/admin/members', label: 'Members' },
      { path: '/admin/labs', label: 'Labs' },
      { path: '/admin/tools', label: 'Tools' },
      { path: '/tools', label: 'App Launcher' },
      { path: '/admin/audit', label: 'Audit Log' },
    ] : []),
    ...(roleName === 'Manager' ? [{ path: '/tools', label: 'App Launcher' }] : []),
  ];

  const navItems = isStaff ? staffNav : orgNav;

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside style={{
        width: 220, background: 'var(--bg-secondary)', borderRight: '1px solid var(--border)',
        padding: '20px 0', display: 'flex', flexDirection: 'column',
      }}>
        <div style={{ padding: '0 16px 24px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 10, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)' }}>
            Corvinus Labs
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, marginTop: 4 }}>Operations</div>
        </div>
        <nav style={{ padding: '16px 8px', flex: 1 }}>
          {navItems.map(item => (
            <Link
              key={item.path}
              to={item.path}
              className={highlightNav === item.path ? 'onboarding-nav-highlight' : undefined}
              style={{
                display: 'block',
                color: location.pathname === item.path || location.pathname.startsWith(item.path + '/') ? 'var(--accent)' : 'var(--text-secondary)',
                padding: '8px 12px',
                borderRadius: 'var(--radius)',
                marginBottom: 2,
                fontSize: 13,
                background: location.pathname === item.path ? 'var(--accent-dim)' : 'transparent',
              }}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </aside>
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column', position: 'relative' }}>
        <header style={{
          background: 'var(--bg-secondary)', padding: '12px 24px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <OrgLabSwitcher />
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ fontSize: 13 }}>
              {user?.name}{' '}
              {isStaff ? (
                <span className="badge badge-staff">Staff</span>
              ) : roleName ? (
                <span className={`badge badge-${roleName.toLowerCase()}`}>{roleName}</span>
              ) : null}
            </span>
            <button className="secondary sm" onClick={logout}>Logout</button>
          </div>
        </header>
        {roleNotice && (
          <div style={{
            background: 'var(--accent-dim)', borderBottom: '1px solid var(--accent)',
            padding: '10px 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            fontSize: 13,
          }}>
            <span>{roleNotice.message}</span>
            <button
              className="sm secondary"
              onClick={() => dismissMutation.mutate(roleNotice.lab_id)}
              disabled={dismissMutation.isPending}
            >
              Dismiss
            </button>
          </div>
        )}
        <div style={{ padding: 24, flex: 1, overflow: 'auto' }}>{children}</div>
        {hasPendingOnboarding && (
          <OnboardingGuide onHighlightChange={setHighlightNav} />
        )}
      </main>
    </div>
  );
}
