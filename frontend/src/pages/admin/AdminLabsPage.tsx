import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function AdminLabsPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');

  const { data: labs } = useQuery({
    queryKey: ['labs', orgId],
    queryFn: () => api<{ id: string; name: string; description: string | null; archived: boolean }[]>(
      `/organizations/${orgId}/labs`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: () => api(`/organizations/${orgId}/labs`, { method: 'POST', body: { name, description }, orgId, token }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['labs'] }); setName(''); setDescription(''); },
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Lab Management</h1>
      <div className="card" style={{ marginBottom: 24 }}>
        <h3>Create Lab</h3>
        <input placeholder="Lab name" value={name} onChange={e => setName(e.target.value)} style={{ marginBottom: 8 }} />
        <input placeholder="Description" value={description} onChange={e => setDescription(e.target.value)} />
        <button style={{ marginTop: 8 }} onClick={() => createMutation.mutate()}>Create</button>
      </div>
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: 8, textAlign: 'left' }}>Name</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Description</th>
            </tr>
          </thead>
          <tbody>
            {labs?.map(l => (
              <tr key={l.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{l.name}</td>
                <td style={{ padding: 8 }}>{l.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
