import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi, getToken, removeToken } from '../api/client';

export interface User {
  id: number;
  email: string;
  username: string;
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: { username_or_email: string; password: string }) => Promise<void>;
  signup: (userData: { email: string; username: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setTokenState] = useState<string | null>(getToken());
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // On mount: check if stored token is valid by fetching current user
  useEffect(() => {
    const initializeAuth = async () => {
      const storedToken = getToken();
      if (storedToken) {
        try {
          const currentUser = await authApi.getCurrentUser();
          setUser(currentUser as User);
          setTokenState(storedToken);
        } catch (error) {
          console.warn('Session expired or invalid token:', error);
          removeToken();
          setUser(null);
          setTokenState(null);
        }
      }
      setIsLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (credentials: { username_or_email: string; password: string }) => {
    const response = await authApi.login(credentials);
    setTokenState(response.access_token);
    setUser(response.user);
  };

  const signup = async (userData: { email: string; username: string; password: string; full_name?: string }) => {
    await authApi.signup(userData);
  };

  const logout = () => {
    authApi.logout();
    setUser(null);
    setTokenState(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user,
        isLoading,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to consume AuthContext cleanly
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};