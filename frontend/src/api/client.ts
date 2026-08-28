const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export interface ApiOptions {
  method?: string;
  body?: unknown;
  orgId?: string | null;
  labId?: string | null;
  token?: string | null;
}

export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const token = options.token ?? localStorage.getItem('token');
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.orgId) headers['X-Organization-Id'] = options.orgId;
  if (options.labId) headers['X-Lab-Id'] = options.labId;

  const res = await fetch(`${API_URL}${path}`, {
    method: options.method || 'GET',
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: { message: res.statusText } }));
    throw new Error(err.error?.message || 'Request failed');
  }
  if (res.status === 204) return {} as T;
  return res.json();
}

export { API_URL };
