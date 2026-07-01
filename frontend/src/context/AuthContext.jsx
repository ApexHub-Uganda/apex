import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { authService } from '../services/authService';
import { getStoredTokens } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const clearSession = useCallback(() => {
    setUser(null);
    setIsAuthenticated(false);
    localStorage.removeItem('apex_user_email');
    localStorage.removeItem('apex_tenant_id');
    queryClient.removeQueries({ queryKey: ['tenant', 'context'] });
    queryClient.removeQueries({ queryKey: ['school-admin-dashboard'] });
  }, [queryClient]);

  const loadUser = useCallback(async () => {
    const { access } = getStoredTokens();
    if (!access) {
      setLoading(false);
      return;
    }

    try {
      const profile = await authService.getProfile();
      setUser(profile);
      setIsAuthenticated(true);
      localStorage.setItem('apex_user_email', profile.email);
      const tenantId = profile.tenant || profile.tenant_id;
      if (tenantId) {
        localStorage.setItem('apex_tenant_id', tenantId);
      }
    } catch {
      clearSession();
    } finally {
      setLoading(false);
    }
  }, [clearSession]);

  useEffect(() => {
    loadUser();
  }, [loadUser]);

  useEffect(() => {
    const handleAuthExpired = () => clearSession();
    window.addEventListener('apex:auth-expired', handleAuthExpired);
    return () => window.removeEventListener('apex:auth-expired', handleAuthExpired);
  }, [clearSession]);

  const login = async (credentials) => {
    const data = await authService.login(credentials);
    setUser(data.user);
    setIsAuthenticated(true);
    localStorage.setItem('apex_user_email', data.user.email);
    await queryClient.invalidateQueries({ queryKey: ['tenant', 'context'] });
    return data;
  };

  const logout = async () => {
    await authService.logout();
    clearSession();
  };

  const updateUser = (updates) => {
    setUser((prev) => (prev ? { ...prev, ...updates } : null));
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        isAuthenticated,
        login,
        logout,
        updateUser,
        isSuperAdmin: user?.role === 'super_admin',
        isSchoolAdmin: user?.role === 'school_admin',
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used within AuthProvider');
  return ctx;
}

export default AuthContext;