import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

interface DemoUser {
  id: string;
  name: string;
  email: string;
  organization_name: string;
  organization_id: string;
  role_name: string;
  lab_name: string | null;
  lab_id: string | null;
}

export default function LoginPage() {
  const { login, token } = useAuth();
  const navigate = useNavigate();

  const { data: users, isLoading } = useQuery({
    queryKey: ['demo-users'],
    queryFn: () => api<DemoUser[]>('/auth/demo-users'),
  });

  if (token) {
    navigate('/');
    return null;
  }

  const handleLogin = async (u: DemoUser) => {
    await login(u.id, u.organization_id, u.lab_id || undefined);
    navigate('/');
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#1a1a2e' }}>
      <div className="card" style={{ width: 560, maxWidth: '90vw' }}>
        <h1 style={{ marginBottom: 8 }}>Corvinus Labs Portal</h1>
        <p style={{ color: '#6c757d', marginBottom: 24 }}>Select a demo user to log in</p>
        {isLoading && <p>Loading users...</p>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {users?.map(u => (
            <button
              key={`${u.id}-${u.organization_name}`}
              className="secondary"
              style={{ textAlign: 'left', padding: 16, display: 'flex', justifyContent: 'space-between' }}
              onClick={() => handleLogin(u)}
            >
              <div>
                <strong>{u.name}</strong>
                <div style={{ fontSize: 13, color: '#6c757d' }}>{u.email}</div>
              </div>
              <div style={{ textAlign: 'right', fontSize: 13 }}>
                <div>{u.organization_name}</div>
                <div><span className="badge badge-active">{u.role_name}</span></div>
                {u.lab_name && <div style={{ color: '#6c757d' }}>{u.lab_name}</div>}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
