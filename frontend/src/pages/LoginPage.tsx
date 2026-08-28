import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface LabRoleSummary {
  lab_id: string;
  lab_name: string;
  lab_role: string;
}

interface MembershipSummary {
  organization_id: string;
  organization_name: string;
  org_role: string;
  effective_role: string;
  labs: LabRoleSummary[];
}

interface DemoUser {
  id: string;
  name: string;
  email: string;
  platform_role: string | null;
  primary_org: string | null;
  primary_role: string | null;
  membership_count: number;
  org_memberships: MembershipSummary[];
}

function formatOrgMembership(m: MembershipSummary) {
  if (m.org_role === 'ADMIN') return `${m.organization_name}: Admin`;
  if (m.labs.length === 0) return `${m.organization_name}: Member`;
  return m.labs.map(l =>
    `${m.organization_name}: ${l.lab_role === 'MANAGER' ? 'Manager' : 'Contributor'} @ ${l.lab_name}`
  ).join(' · ');
}

export default function LoginPage() {
  const { login, token } = useAuth();
  const navigate = useNavigate();

  const { data: users, isLoading } = useQuery({
    queryKey: ['demo-users'],
    queryFn: () => api<DemoUser[]>('/auth/demo-users'),
  });

  if (token) {
    navigate('/');
    return null;
  }

  const handleLogin = async (userId: string, isStaff: boolean) => {
    await login(userId);
    navigate(isStaff ? '/platform' : '/');
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--bg-primary)',
    }}>
      <div style={{ width: 520, maxWidth: '90vw' }}>
        <div style={{ marginBottom: 32, textAlign: 'center' }}>
          <div style={{ fontSize: 11, letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--accent)', marginBottom: 8 }}>
            Corvinus Labs
          </div>
          <h1 style={{ fontSize: 24, marginBottom: 8 }}>Operations Portal</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>Select a demo identity — users can belong to multiple orgs and labs with different roles</p>
        </div>

        {isLoading && <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>Loading...</p>}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {users?.map(u => (
            <button
              key={u.id}
              className="secondary"
              style={{
                textAlign: 'left', padding: '14px 16px',
                display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12,
              }}
              onClick={() => handleLogin(u.id, u.platform_role === 'STAFF')}
            >
              <div>
                <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.name}</div>
                <div className="mono">{u.email}</div>
                {u.org_memberships?.length > 0 && (
                  <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 2 }}>
                    {u.org_memberships.flatMap(m =>
                      m.org_role === 'ADMIN'
                        ? [<span key={m.organization_id} style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatOrgMembership(m)}</span>]
                        : m.labs.length > 0
                          ? m.labs.map(l => (
                            <span key={`${m.organization_id}-${l.lab_id}`} style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                              {m.organization_name}: {l.lab_role === 'MANAGER' ? 'Manager' : 'Contributor'} @ {l.lab_name}
                            </span>
                          ))
                          : [<span key={m.organization_id} style={{ fontSize: 11, color: 'var(--text-muted)' }}>{m.organization_name}: Member</span>]
                    )}
                  </div>
                )}
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                {u.platform_role === 'STAFF' ? (
                  <span className="badge badge-staff">Staff</span>
                ) : (
                  <>
                    {u.membership_count > 1 && (
                      <span className="badge badge-contributor" style={{ marginBottom: 4 }}>{u.membership_count} orgs</span>
                    )}
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{u.primary_org}</div>
                    <span className={`badge badge-${u.primary_role?.toLowerCase()}`}>{u.primary_role}</span>
                  </>
                )}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
