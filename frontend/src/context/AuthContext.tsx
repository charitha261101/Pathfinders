import React, { createContext, useContext, useState, useEffect } from 'react';

export interface AuthenticatedUser {
  userId: string;
  fullName: string;
  emailAddress: string;
  userRole: string;
  organizationName?: string;
  initials: string;
  token: string;
  redirectPath: string;
}

interface AuthenticationContext {
  currentUser: AuthenticatedUser | null;
  authenticate: (emailAddress: string, password: string) => Promise<AuthenticatedUser>;
  signOut: () => void;
  hasAdminAccess: boolean;
  isAuthLoading: boolean;
}

const AuthContext = createContext<AuthenticationContext>(null!);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [currentUser, setCurrentUser] = useState<AuthenticatedUser | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  useEffect(() => {
    const storedUserData = localStorage.getItem('pathwise_user');
    if (storedUserData) {
      try {
        setCurrentUser(JSON.parse(storedUserData));
      } catch {
        // Corrupted storage, ignore
      }
    }
    setIsAuthLoading(false);
  }, []);

  const authenticate = async (emailAddress: string, password: string): Promise<AuthenticatedUser> => {
    // Try v2 (DB-backed) first, fall back to v1 (in-memory)
    let response = await fetch('/api/v1/auth/login/v2', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: emailAddress, password }),
    });
    if (response.status === 404) {
      response = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: emailAddress, password }),
      });
    }
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(errorData.detail || 'Authentication failed');
    }
    const responseData = await response.json();
    const authenticatedUser: AuthenticatedUser = {
      userId: responseData.user_id || responseData.id || '',
      fullName: responseData.name || responseData.email || '',
      emailAddress: responseData.email || '',
      userRole: responseData.role || 'BUSINESS_OWNER',
      organizationName: responseData.company || '',
      initials:
        responseData.avatar_initials || responseData.name?.slice(0, 2).toUpperCase() || 'U',
      token: responseData.access_token || responseData.token || '',
      redirectPath:
        responseData.redirect_to ||
        (responseData.role === 'SUPER_ADMIN' ? '/admin/dashboard' : '/user/dashboard'),
    };
    localStorage.setItem('pathwise_user', JSON.stringify(authenticatedUser));
    setCurrentUser(authenticatedUser);
    return authenticatedUser;
  };

  const signOut = () => {
    localStorage.removeItem('pathwise_user');
    localStorage.removeItem('pathwise_token');
    localStorage.removeItem('pathwise_role');
    localStorage.removeItem('pathwise_email');
    setCurrentUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider
      value={{
        currentUser,
        authenticate,
        signOut,
        hasAdminAccess: currentUser?.userRole === 'SUPER_ADMIN',
        isAuthLoading,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
