import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

export default function AdminToolsPage() {
  const { orgId, token } = useAuth();
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [type, setType] = useState('cvat');

  const { data: tools } = useQuery({
    queryKey: ['tools', orgId],
    queryFn: () => api<{ id: string; name: string; type: string; status: string; description: string | null }[]>(
      `/organizations/${orgId}/tools`, { orgId, token }
    ),
    enabled: !!orgId,
  });

  const createMutation = useMutation({
    mutationFn: () => api(`/organizations/${orgId}/tools`, {
      method: 'POST', body: { name, type, description: `${name} integration` }, orgId, token,
    }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['tools'] }); setName(''); },
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Tool Registry</h1>
      <div className="card" style={{ marginBottom: 24 }}>
        <h3>Register Tool</h3>
        <input placeholder="Tool name" value={name} onChange={e => setName(e.target.value)} style={{ marginBottom: 8 }} />
        <select value={type} onChange={e => setType(e.target.value)}>
          <option value="cvat">CVAT</option>
          <option value="isaac_sim">Isaac Sim</option>
          <option value="google_drive">Google Drive</option>
        </select>
        <button style={{ marginTop: 8 }} onClick={() => createMutation.mutate()}>Register</button>
      </div>
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: 8, textAlign: 'left' }}>Name</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Type</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {tools?.map(t => (
              <tr key={t.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{t.name}</td>
                <td style={{ padding: 8 }}>{t.type}</td>
                <td style={{ padding: 8 }}>{t.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
