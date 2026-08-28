import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

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

interface MeData {
  organizations: { id: string; name: string }[];
  labs: { id: string; name: string; organization_id: string }[];
  memberships: { organization_id: string; org_role: string }[];
  membership_summaries: MembershipSummary[];
  lab_memberships: { lab_id: string; lab_name: string; organization_id: string; lab_role: string }[];
}

function roleBadge(orgRole: string, labRole?: string) {
  if (orgRole === 'ADMIN') return { label: 'Admin', cls: 'admin' };
  if (labRole === 'MANAGER') return { label: 'Manager', cls: 'manager' };
  if (labRole === 'CONTRIBUTOR') return { label: 'Contributor', cls: 'contributor' };
  return { label: 'Member', cls: 'contributor' };
}

function orgOptionLabel(orgName: string, summary?: MembershipSummary) {
  if (!summary) return orgName;
  if (summary.org_role === 'ADMIN') return `${orgName} — Admin`;
  if (summary.labs.length === 0) return `${orgName} — Member`;
  if (summary.labs.length === 1) {
    return `${orgName} — ${summary.labs[0].lab_role === 'MANAGER' ? 'Manager' : 'Contributor'} @ ${summary.labs[0].lab_name}`;
  }
  const roles = summary.labs.map(l => `${l.lab_role === 'MANAGER' ? 'Mgr' : 'Contrib'}@${l.lab_name.split(' ')[0]}`).join(', ');
  return `${orgName} — ${roles}`;
}

export default function OrgLabSwitcher() {
  const { orgId, labId, setOrgId, setLabId, isStaff } = useAuth();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<MeData>('/auth/me'),
    enabled: !isStaff,
  });

  if (isStaff) {
    return <span className="mono" style={{ color: 'var(--text-muted)' }}>Platform · Corvinus Staff</span>;
  }

  const orgs = data?.organizations || [];
  const summaries = data?.membership_summaries || [];
  const orgMembership = data?.memberships.find(m => m.organization_id === orgId);
  const orgRole = orgMembership?.org_role || 'MEMBER';
  const currentSummary = summaries.find(s => s.organization_id === orgId);
  const labMemberships = (data?.lab_memberships || []).filter(lm => lm.organization_id === orgId);
  const currentLabMembership = labMemberships.find(lm => lm.lab_id === labId);
  const badge = roleBadge(orgRole, currentLabMembership?.lab_role);

  const handleOrgChange = (newOrgId: string) => {
    const summary = summaries.find(s => s.organization_id === newOrgId);
    const defaultLab = summary && summary.org_role !== 'ADMIN' && summary.labs.length > 0
      ? summary.labs[0].lab_id
      : null;
    setOrgId(newOrgId, defaultLab);
    queryClient.clear();
  };

  const handleLabChange = (newLabId: string) => {
    setLabId(newLabId || null);
    queryClient.invalidateQueries();
  };

  const showOrgSwitcher = orgs.length > 1;
  const showLabSwitcher = labMemberships.length > 0 && orgRole !== 'ADMIN';

  if (!showOrgSwitcher && !showLabSwitcher) {
    const org = orgs.find(o => o.id === orgId);
    const lab = labMemberships.find(l => l.lab_id === labId);
    return (
      <span className="mono" style={{ color: 'var(--text-muted)' }}>
        {org?.name}{lab ? ` / ${lab.lab_name}` : ''} · <span className={`badge badge-${badge.cls}`}>{badge.label}</span>
      </span>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
      {showOrgSwitcher && (
        <select value={orgId || ''} onChange={e => handleOrgChange(e.target.value)} style={{ width: 'auto', minWidth: 220 }}>
          {orgs.map(o => {
            const summary = summaries.find(s => s.organization_id === o.id);
            return (
              <option key={o.id} value={o.id}>{orgOptionLabel(o.name, summary)}</option>
            );
          })}
        </select>
      )}
      {!showOrgSwitcher && orgs[0] && (
        <span className="mono">{orgs.find(o => o.id === orgId)?.name}</span>
      )}
      {showLabSwitcher && (
        <select value={labId || ''} onChange={e => handleLabChange(e.target.value)} style={{ width: 'auto', minWidth: 180 }}>
          {labMemberships.length > 1 && <option value="">Select lab</option>}
          {labMemberships.map(lm => (
            <option key={lm.lab_id} value={lm.lab_id}>
              {lm.lab_name} ({lm.lab_role === 'MANAGER' ? 'Manager' : 'Contributor'})
            </option>
          ))}
        </select>
      )}
      <span className={`badge badge-${badge.cls}`}>{badge.label}</span>
      {currentSummary && currentSummary.labs.length > 1 && orgRole !== 'ADMIN' && (
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
          {currentSummary.labs.length} labs
        </span>
      )}
    </div>
  );
}
