import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api/client';

export default function InviteAcceptPage() {
  const { token: inviteToken } = useParams();
  const navigate = useNavigate();
  const [name, setName] = useState('');

  const { data: invitation, isLoading } = useQuery({
    queryKey: ['invitation', inviteToken],
    queryFn: () => api<{ email: string; status: string; expires_at: string }>(`/invitations/${inviteToken}`),
    enabled: !!inviteToken,
  });

  const acceptMutation = useMutation({
    mutationFn: () => api(`/invitations/${inviteToken}/accept`, {
      method: 'POST',
      body: { name: name || undefined },
      token: localStorage.getItem('token'),
    }),
    onSuccess: () => navigate('/login'),
  });

  if (isLoading) return <div style={{ padding: 40 }}>Loading invitation...</div>;
  if (!invitation) return <div style={{ padding: 40 }}>Invitation not found</div>;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="card" style={{ width: 400 }}>
        <h2>Accept Invitation</h2>
        <p>You've been invited to join as <strong>{invitation.email}</strong></p>
        <p style={{ fontSize: 13, color: '#6c757d' }}>Status: {invitation.status}</p>
        <input placeholder="Your name (if new user)" value={name} onChange={e => setName(e.target.value)} style={{ marginBottom: 12 }} />
        <button onClick={() => acceptMutation.mutate()}>Accept Invitation</button>
      </div>
    </div>
  );
}
