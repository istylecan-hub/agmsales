import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const API_URL = process.env.REACT_APP_BACKEND_URL;

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check if there's a valid token on mount (from sessionStorage for page refresh)
  useEffect(() => {
    const savedToken = sessionStorage.getItem('auth_token');
    if (savedToken) {
      // Verify token is still valid
      verifyToken(savedToken);
    } else {
      setIsLoading(false);
    }
  }, []);

  const verifyToken = async (tokenToVerify) => {
    try {
      const res = await fetch(`${API_URL}/api/auth/verify`, {
        headers: {
          'Authorization': `Bearer ${tokenToVerify}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setToken(tokenToVerify);
        setUser({ username: data.username });
      } else {
        // Token invalid, clear it
        sessionStorage.removeItem('auth_token');
        setToken(null);
        setUser(null);
      }
    } catch (err) {
      console.error('Token verification failed:', err);
      sessionStorage.removeItem('auth_token');
      setToken(null);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = useCallback(async (username, password) => {
    try {
      const res = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      });

      const data = await res.json();

      if (res.ok && data.access_token) {
        setToken(data.access_token);
        setUser({ username });
        // Save to sessionStorage for page refresh persistence
        sessionStorage.setItem('auth_token', data.access_token);
        return { success: true };
      } else {
        return { success: false, error: data.detail || 'Login failed' };
      }
    } catch (err) {
      console.error('Login error:', err);
      return { success: false, error: 'Network error' };
    }
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    sessionStorage.removeItem('auth_token');
  }, []);

  // Helper function to make authenticated API calls
  const authFetch = useCallback(async (url, options = {}) => {
    if (!token) {
      throw new Error('Not authenticated');
    }

    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${token}`,
    };

    // Don't set Content-Type for FormData (let browser set it with boundary)
    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }

    const res = await fetch(url, {
      ...options,
      headers,
    });

    // If 401, logout and redirect
    if (res.status === 401) {
      logout();
      window.location.href = '/login';
      throw new Error('Session expired');
    }

    return res;
  }, [token, logout]);

  const value = {
    token,
    user,
    isAuthenticated: !!token,
    isLoading,
    login,
    logout,
    authFetch,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
