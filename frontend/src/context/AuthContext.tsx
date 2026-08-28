/**
 * Auth session: demo login token + active org/lab IDs in localStorage.
 * All API calls should send these via the client headers.
 */
import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { api } from '../api/client';

interface User {
  id: string;
  name: string;
  email: string;
  platform_role?: string | null;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isStaff: boolean;
  orgId: string | null;
  labId: string | null;
  login: (userId: string) => Promise<void>;
  logout: () => void;
  setOrgId: (id: string, defaultLabId?: string | null) => void;
  setLabId: (id: string | null) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const stored = localStorage.getItem('user');
    return stored ? JSON.parse(stored) : null;
  });
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('token'));
  const [isStaff, setIsStaff] = useState(() => localStorage.getItem('isStaff') === 'true');
  const [orgId, setOrgIdState] = useState<string | null>(() => localStorage.getItem('orgId'));
  const [labId, setLabIdState] = useState<string | null>(() => localStorage.getItem('labId'));

  const login = useCallback(async (userId: string) => {
    const res = await api<{
      access_token: string;
      user: User;
      is_staff: boolean;
      default_organization_id: string | null;
      default_lab_id: string | null;
    }>('/auth/demo-login', { method: 'POST', body: { user_id: userId } });

    localStorage.setItem('token', res.access_token);
    localStorage.setItem('user', JSON.stringify(res.user));
    localStorage.setItem('isStaff', String(res.is_staff));

    setToken(res.access_token);
    setUser(res.user);
    setIsStaff(res.is_staff);

    if (res.is_staff) {
      localStorage.removeItem('orgId');
      localStorage.removeItem('labId');
      setOrgIdState(null);
      setLabIdState(null);
    } else {
      localStorage.setItem('orgId', res.default_organization_id!);
      if (res.default_lab_id) localStorage.setItem('labId', res.default_lab_id);
      else localStorage.removeItem('labId');
      setOrgIdState(res.default_organization_id);
      setLabIdState(res.default_lab_id);
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.clear();
    setToken(null);
    setUser(null);
    setIsStaff(false);
    setOrgIdState(null);
    setLabIdState(null);
  }, []);

  const setOrgId = useCallback((id: string, defaultLabId?: string | null) => {
    localStorage.setItem('orgId', id);
    setOrgIdState(id);
    if (defaultLabId) {
      localStorage.setItem('labId', defaultLabId);
      setLabIdState(defaultLabId);
    } else {
      localStorage.removeItem('labId');
      setLabIdState(null);
    }
  }, []);

  const setLabId = useCallback((id: string | null) => {
    if (id) localStorage.setItem('labId', id);
    else localStorage.removeItem('labId');
    setLabIdState(id);
  }, []);

  return (
    <AuthContext.Provider value={{ user, token, isStaff, orgId, labId, login, logout, setOrgId, setLabId }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
