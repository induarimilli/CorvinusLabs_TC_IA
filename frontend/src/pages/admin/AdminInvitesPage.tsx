import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function AdminInvitesPage() {
  const { orgId, token } = useAuth();
  const [email, setEmail] = useState('');
  const [roleId, setRoleId] = useState('');
  const [labId, setLabId] = useState('');
  const [inviteLink, setInviteLink] = useState('');

  const { data: roles } = useQuery({
    queryKey: ['roles', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/roles`, { orgId, token }),
    enabled: !!orgId,
  });

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/labs`, { orgId, token }),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: () => api<{ invite_link: string }>(`/organizations/${orgId}/invitations`, {
      method: 'POST',
      body: { email, role_id: roleId, lab_id: labId || null },
      orgId, token,
    }),
    onSuccess: (data) => setInviteLink(data.invite_link),
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Invitations</h1>
      <div className="card">
        <h3>Invite User</h3>
        <input placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} style={{ marginBottom: 8 }} />
        <select value={roleId} onChange={e => setRoleId(e.target.value)} style={{ marginBottom: 8 }}>
          <option value="">Select role</option>
          {roles?.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
        <select value={labId} onChange={e => setLabId(e.target.value)} style={{ marginBottom: 8 }}>
          <option value="">Select lab (optional)</option>
          {labs?.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
        </select>
        <button onClick={() => createMutation.mutate()}>Create Invitation</button>
        {inviteLink && (
          <div style={{ marginTop: 16, padding: 12, background: '#e9ecef', borderRadius: 6 }}>
            <strong>Invite link:</strong>
            <div style={{ wordBreak: 'break-all', marginTop: 4 }}>
              <a href={inviteLink} target="_blank" rel="noreferrer">{inviteLink}</a>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
