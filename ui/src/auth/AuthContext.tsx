import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import * as api from '../api/client'

// ── Types ────────────────────────────────────────────────────────────

interface JWTPayload {
  sub?: string
  username?: string
  is_admin?: boolean
  role?: string
  roles?: string[]
  [key: string]: unknown
}

interface AuthContextValue {
  user: JWTPayload | null
  token: string | null
  login: (username: string, password: string) => Promise<api.LoginResponse>
  logout: () => void
  isAuthenticated: boolean
  isAdmin: boolean
}

interface AuthProviderProps {
  children: React.ReactNode
}

// ── Context ──────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

function decodeJWT(token: string): JWTPayload | null {
  try {
    const payload = token.split('.')[1]
    const decoded: JWTPayload = JSON.parse(atob(payload))
    return decoded
  } catch {
    return null
  }
}

export function AuthProvider({ children }: AuthProviderProps): React.ReactElement {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem('nmia_token'))
  const [user, setUser] = useState<JWTPayload | null>(() => {
    const t = localStorage.getItem('nmia_token')
    return t ? decodeJWT(t) : null
  })

  useEffect(() => {
    if (token) {
      localStorage.setItem('nmia_token', token)
      const decoded = decodeJWT(token)
      setUser(decoded)
    } else {
      localStorage.removeItem('nmia_token')
      setUser(null)
    }
  }, [token])

  const login = useCallback(async (username: string, password: string): Promise<api.LoginResponse> => {
    const response = await api.login(username, password)
    const accessToken = response.data.access_token
    setToken(accessToken)
    return response.data
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const isAuthenticated = !!token
  const isAdmin =
    user?.is_admin === true ||
    user?.role === 'admin' ||
    (Array.isArray(user?.roles) && user.roles.includes('admin'))

  const value: AuthContextValue = { user, token, login, logout, isAuthenticated, isAdmin }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

export default AuthContext
