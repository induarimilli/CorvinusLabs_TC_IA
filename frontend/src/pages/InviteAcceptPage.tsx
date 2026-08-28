import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function InviteAcceptPage() {
  const { token: inviteToken } = useParams();
  const navigate = useNavigate();
  const { login } = useAuth();
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const { data: invitation, isLoading } = useQuery({
    queryKey: ['invitation', inviteToken],
    queryFn: () => api<{ email: string; status: string; lab_role: string; expires_at: string }>(`/invitations/${inviteToken}`),
    enabled: !!inviteToken,
  });

  const acceptMutation = useMutation({
    mutationFn: () => api<{ user_id: string; organization_id: string }>(`/invitations/${inviteToken}/accept`, {
      method: 'POST',
      body: { name: name || undefined },
      token: localStorage.getItem('token'),
    }),
    onSuccess: async (data) => {
      setSuccess(true);
      setError('');
      // If not logged in, they'll need to pick themselves on login page
      setTimeout(() => navigate('/login'), 2000);
    },
    onError: (e: Error) => setError(e.message),
  });

  if (isLoading) return <div style={{ padding: 40, color: 'var(--text-muted)' }}>Loading invitation...</div>;
  if (!invitation) return <div style={{ padding: 40 }}>Invitation not found.</div>;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
      <div className="card" style={{ width: 420 }}>
        <h2 style={{ marginBottom: 8 }}>Accept Invitation</h2>
        <p style={{ color: 'var(--text-secondary)', marginBottom: 16 }}>
          You've been invited as <strong>{invitation.lab_role}</strong> for <span className="mono">{invitation.email}</span>
        </p>
        {invitation.status !== 'PENDING' && (
          <div className="error-banner">This invitation is {invitation.status.toLowerCase()}.</div>
        )}
        {error && <div className="error-banner">{error}</div>}
        {success && <p style={{ color: 'var(--accent)' }}>Accepted! Redirecting to login...</p>}
        {!success && invitation.status === 'PENDING' && (
          <>
            <div className="form-row">
              <label>Your name (if new user)</label>
              <input value={name} onChange={e => setName(e.target.value)} placeholder="Full name" />
            </div>
            <button onClick={() => acceptMutation.mutate()} disabled={acceptMutation.isPending}>
              Accept Invitation
            </button>
          </>
        )}
      </div>
    </div>
  );
}
