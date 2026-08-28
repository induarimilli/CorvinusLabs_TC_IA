import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface LabMember {
  user_id: string;
  name: string;
  email: string;
  lab_role: string;
}

export default function TeamPage() {
  const { orgId, labId, token, user } = useAuth();
  const queryClient = useQueryClient();
  const [grantToolId, setGrantToolId] = useState('');
  const [grantUserId, setGrantUserId] = useState('');

  const { data: me } = useQuery({
    queryKey: ['me'],
    queryFn: () => api<{
      memberships: { organization_id: string; org_role: string }[];
      lab_memberships: { lab_id: string; organization_id: string; lab_role: string }[];
    }>('/auth/me'),
  });

  const orgRole = me?.memberships.find(m => m.organization_id === orgId)?.org_role || '';
  const myLabRole = me?.lab_memberships.find(l => l.organization_id === orgId && l.lab_id === labId)?.lab_role;
  const isAdmin = orgRole === 'ADMIN';
  const isManager = myLabRole === 'MANAGER';
  const isContributor = myLabRole === 'CONTRIBUTOR';

  const { data: labMembers } = useQuery({
    queryKey: ['lab-members', orgId, labId],
    queryFn: () => api<LabMember[]>(`/organizations/${orgId}/labs/${labId}/members`, { orgId, token }),
    enabled: !!orgId && !!labId,
  });

  const members = labMembers?.map(m => ({
    id: m.user_id,
    name: m.name,
    email: m.email,
    role: m.lab_role,
    status: 'ACTIVE',
  }));

  const { data: tools } = useQuery({
    queryKey: ['tools', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/tools`, { orgId, token }),
    enabled: !!orgId && isManager,
  });

  const { data: accessList } = useQuery({
    queryKey: ['tool-access', orgId],
    queryFn: () => api<{ access: { id: string; tool_id: string; user_id: string; provisioning_status: string }; tool_name: string; user_name: string }[]>(
      `/organizations/${orgId}/tool-access`, { orgId, token }
    ),
    enabled: !!orgId && isManager,
    refetchInterval: 3000,
  });

  const grantMutation = useMutation({
    mutationFn: () => api(`/tools/${grantToolId}/access`, {
      method: 'POST', body: { user_id: grantUserId, access_level: 'view' }, orgId, token,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tool-access'] });
      setGrantToolId('');
      setGrantUserId('');
    },
  });

  if (!isAdmin && !isManager && !isContributor) {
    return (
      <div>
        <div className="page-header"><h1>Team</h1></div>
        <div className="card">Select a lab to view team members.</div>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <h1>{isManager ? 'Lab Team' : 'Lab Members'}</h1>
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <h3 style={{ marginBottom: 12 }}>Members</h3>
        <table>
          <thead>
            <tr><th>Name</th><th>Email</th><th>Lab Role</th></tr>
          </thead>
          <tbody>
            {members?.map(m => (
              <tr key={m.id}>
                <td>{m.name}</td>
                <td className="mono">{m.email}</td>
                <td><span className={`badge badge-${m.role.toLowerCase()}`}>{m.role}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isManager && (
        <>
          <div className="card" style={{ marginBottom: 24 }}>
            <h3 style={{ marginBottom: 12 }}>Grant Tool Access</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: 12, alignItems: 'end' }}>
              <div className="form-row">
                <label>Member</label>
                <select value={grantUserId} onChange={e => setGrantUserId(e.target.value)}>
                  <option value="">Select member</option>
                  {members?.filter(m => m.role === 'CONTRIBUTOR').map(m => (
                    <option key={m.id} value={m.id}>{m.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-row">
                <label>Tool</label>
                <select value={grantToolId} onChange={e => setGrantToolId(e.target.value)}>
                  <option value="">Select tool</option>
                  {tools?.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
              </div>
              <button onClick={() => grantMutation.mutate()} disabled={!grantToolId || !grantUserId}>Grant</button>
            </div>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 12 }}>Tool Access</h3>
            <table>
              <thead>
                <tr><th>User</th><th>Tool</th><th>Status</th></tr>
              </thead>
              <tbody>
                {accessList?.map(({ access, tool_name, user_name }) => (
                  <tr key={access.id}>
                    <td>{user_name}</td>
                    <td>{tool_name}</td>
                    <td>
                      <span className={`badge badge-${access.provisioning_status === 'ACTIVE' ? 'active' : access.provisioning_status === 'FAILED' ? 'failed' : 'provisioning'}`}>
                        {access.provisioning_status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
