/** Accept invite: shows org/lab/role; switches session to invitee even if another user was logged in. */
import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation } from '@tanstack/react-query';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function InviteAcceptPage() {
  const { token: inviteToken } = useParams();
  const navigate = useNavigate();
  const { login, logout, user } = useAuth();
  const [name, setName] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const { data: invitation, isLoading } = useQuery({
    queryKey: ['invitation', inviteToken],
    queryFn: () => api<{
      email: string;
      status: string;
      lab_role: string | null;
      org_role: string | null;
      organization_name: string;
      lab_name: string | null;
      role_display: string | null;
      confirmation_message: string;
      expires_at: string;
    }>(`/invitations/${inviteToken}`),
    enabled: !!inviteToken,
  });

  const loggedInMismatch = user && invitation && user.email.toLowerCase() !== invitation.email.toLowerCase();

  const acceptMutation = useMutation({
    mutationFn: async () => {
      const data = await api<{
        user_id: string;
        organization_id: string;
        lab_id: string | null;
        onboarding_required: boolean;
      }>(`/invitations/${inviteToken}/accept`, {
        method: 'POST',
        body: { name: name || undefined },
        token: null,
      });
      return data;
    },
    onSuccess: async (data) => {
      setSuccess(true);
      setError('');
      logout();
      await login(data.user_id);
      localStorage.setItem('orgId', data.organization_id);
      if (data.lab_id) localStorage.setItem('labId', data.lab_id);
      setTimeout(() => navigate(data.onboarding_required ? '/' : '/'), 1500);
    },
    onError: (e: Error) => setError(e.message),
  });

  if (isLoading) return <div style={{ padding: 40, color: 'var(--text-muted)' }}>Loading invitation...</div>;
  if (!invitation) return <div style={{ padding: 40 }}>Invitation not found.</div>;

  const roleLabel = invitation.org_role === 'ADMIN'
    ? 'Organization Admin'
    : `${invitation.lab_role} in ${invitation.lab_name}`;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
      <div className="card" style={{ width: 480 }}>
        <h2 style={{ marginBottom: 8 }}>Accept Invitation</h2>
        <div style={{ marginBottom: 16, fontSize: 14, color: 'var(--text-secondary)' }}>
          <div><strong>Organization:</strong> {invitation.organization_name}</div>
          {invitation.lab_name && <div><strong>Lab:</strong> {invitation.lab_name}</div>}
          <div><strong>Role:</strong> {roleLabel}</div>
          <div style={{ marginTop: 8 }} className="mono">{invitation.email}</div>
        </div>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.5 }}>
          {invitation.confirmation_message}
        </p>
        {loggedInMismatch && (
          <p style={{ fontSize: 13, color: 'var(--warning)', marginBottom: 12 }}>
            You're signed in as {user?.email}. Accepting will switch you to {invitation.email}.
          </p>
        )}
        {invitation.status !== 'PENDING' && (
          <div className="error-banner">This invitation is {invitation.status.toLowerCase()}.</div>
        )}
        {error && <div className="error-banner">{error}</div>}
        {success && <p style={{ color: 'var(--accent)' }}>Accepted! Redirecting...</p>}
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
