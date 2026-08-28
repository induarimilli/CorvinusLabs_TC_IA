import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface MeData {
  organizations: { id: string; name: string }[];
  labs: { id: string; name: string; organization_id: string }[];
  memberships: { organization_id: string; role_name: string }[];
}

export default function OrgLabSwitcher() {
  const { orgId, labId, setOrgId, setLabId } = useAuth();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<MeData>('/auth/me'),
  });

  const orgs = data?.organizations || [];
  const labs = (data?.labs || []).filter(l => l.organization_id === orgId);

  const handleOrgChange = (newOrgId: string) => {
    setOrgId(newOrgId);
    queryClient.invalidateQueries();
  };

  const handleLabChange = (newLabId: string) => {
    setLabId(newLabId || null);
    queryClient.invalidateQueries();
  };

  if (orgs.length <= 1 && labs.length <= 1) {
    const org = orgs.find(o => o.id === orgId);
    const lab = labs.find(l => l.id === labId);
    return (
      <span style={{ fontSize: 14, color: '#6c757d' }}>
        {org?.name}{lab ? ` / ${lab.name}` : ''}
      </span>
    );
  }

  return (
    <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
      {orgs.length > 1 && (
        <select value={orgId || ''} onChange={e => handleOrgChange(e.target.value)}>
          {orgs.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
        </select>
      )}
      {labs.length > 0 && (
        <select value={labId || ''} onChange={e => handleLabChange(e.target.value)}>
          <option value="">All labs</option>
          {labs.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
      )}
    </div>
  );
}
