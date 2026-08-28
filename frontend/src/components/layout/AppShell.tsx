import { Link, useLocation, Navigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';
import OrgLabSwitcher from './OrgLabSwitcher';

interface MeResponse {
  memberships: { organization_id: string; org_role: string }[];
  lab_memberships: { lab_id: string; organization_id: string; lab_role: string }[];
  is_staff: boolean;
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
  const { user, logout, orgId, labId, isStaff, token } = useAuth();
  const location = useLocation();

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<MeResponse>('/auth/me'),
  });

  if (isStaff && !location.pathname.startsWith('/platform')) {
    return <Navigate to="/platform" replace />;
  }

  if (!isStaff && !orgId && location.pathname !== '/login') {
    return <Navigate to="/login" replace />;
  }

  const orgMembership = me?.memberships.find(m => m.organization_id === orgId);
  const orgRole = orgMembership?.org_role || '';
  const roleName = effectiveRole(orgRole, labId, me?.lab_memberships || [], orgId);

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
      <main style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
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
        <div style={{ padding: 24, flex: 1, overflow: 'auto' }}>{children}</div>
      </main>
    </div>
  );
}
