import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function AdminMembersPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();

  const { data: members } = useQuery({
    queryKey: ['members-details', orgId],
    queryFn: () => api<{ membership: { id: string; role_id: string; role_name: string; status: string }; user: { id: string; name: string; email: string } }[]>(
      `/organizations/${orgId}/members/details`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const { data: roles } = useQuery({
    queryKey: ['roles', orgId],
    queryFn: () => api<{ id: string; name: string }[]>(`/organizations/${orgId}/roles`, { orgId, token }),
    enabled: !!orgId,
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, role_id }: { id: string; role_id: string }) =>
      api(`/organizations/${orgId}/members/${id}`, { method: 'PATCH', body: { role_id }, orgId, token }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['members-details'] }),
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Member Management</h1>
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: 8, textAlign: 'left' }}>Name</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Email</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Role</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {members?.map(({ user, membership }) => (
              <tr key={membership.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{user.name}</td>
                <td style={{ padding: 8 }}>{user.email}</td>
                <td style={{ padding: 8 }}>
                  <select value={membership.role_id}
                    onChange={e => updateMutation.mutate({ id: membership.id, role_id: e.target.value })}>
                    {roles?.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
                  </select>
                </td>
                <td style={{ padding: 8 }}>{membership.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
