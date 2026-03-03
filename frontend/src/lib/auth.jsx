import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { getToken, setToken, setOnUnauthorized, getMe } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setOnUnauthorized(logout);
  }, [logout]);

  useEffect(() => {
    const t = getToken();
    if (t) {
      getMe()
        .then((u) => {
          u.role_name = u.role?.name || 'agent';
          setUser(u);
        })
        .catch(() => setToken(null))
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, loading, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
