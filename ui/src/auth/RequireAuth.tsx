import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthContext'

interface RequireAuthProps {
  children: React.ReactNode
  requireAdmin?: boolean
}

export default function RequireAuth({ children, requireAdmin = false }: RequireAuthProps): React.ReactElement {
  const { isAuthenticated, isAdmin } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/identities" replace />
  }

  return <>{children}</>
}
