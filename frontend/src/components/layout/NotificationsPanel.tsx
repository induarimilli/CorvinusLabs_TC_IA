import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api/client';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}

export default function NotificationsPanel() {
  const { orgId, token } = useAuth();

  const { data: notifications } = useQuery({
    queryKey: ['notifications', orgId],
    queryFn: () => api<Notification[]>(`/organizations/${orgId}/notifications`, { orgId, token }),
    enabled: !!orgId && !!token,
  });

  if (!notifications?.length) return null;

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <h3>Notifications</h3>
      <ul style={{ listStyle: 'none', marginTop: 12 }}>
        {notifications.slice(0, 5).map(n => (
          <li key={n.id} style={{ padding: '8px 0', borderBottom: '1px solid #eee', opacity: n.is_read ? 0.6 : 1 }}>
            <strong>{n.title}</strong>
            <div style={{ fontSize: 13, color: '#6c757d' }}>{n.message}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
