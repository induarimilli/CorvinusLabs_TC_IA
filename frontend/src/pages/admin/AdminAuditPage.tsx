import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface AuditEvent {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  actor_user_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export default function AdminAuditPage() {
  const { orgId, token } = useAuth();

  const { data: events } = useQuery({
    queryKey: ['audit', orgId],
    queryFn: () => api<AuditEvent[]>(`/organizations/${orgId}/audit-events`, { orgId, token }),
    enabled: !!orgId,
  });

  return (
    <div>
      <h1 style={{ marginBottom: 24 }}>Audit Log</h1>
      <div className="card">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
          <thead>
            <tr style={{ borderBottom: '2px solid #dee2e6' }}>
              <th style={{ padding: 8, textAlign: 'left' }}>Time</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Action</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Entity</th>
              <th style={{ padding: 8, textAlign: 'left' }}>Actor</th>
            </tr>
          </thead>
          <tbody>
            {events?.map(e => (
              <tr key={e.id} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: 8 }}>{new Date(e.created_at).toLocaleString()}</td>
                <td style={{ padding: 8 }}>{e.action}</td>
                <td style={{ padding: 8 }}>{e.entity_type} {e.entity_id?.slice(0, 8)}</td>
                <td style={{ padding: 8 }}>{e.actor_user_id?.slice(0, 8) || '—'}</td>
              </tr>
            ))}
            {events?.length === 0 && (
              <tr><td colSpan={4} style={{ padding: 16, textAlign: 'center', color: '#6c757d' }}>No audit events yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
