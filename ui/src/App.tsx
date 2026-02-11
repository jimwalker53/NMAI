import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './auth/AuthContext'
import RequireAuth from './auth/RequireAuth'
import AppShell from './layout/AppShell'
import Login from './auth/Login'
import Enclaves from './pages/Enclaves'
import Users from './pages/Users'
import Connectors from './pages/Connectors'
import ConnectorDetail from './pages/ConnectorDetail'
import Identities from './pages/Identities'
import IdentityDetail from './pages/IdentityDetail'
import Reports from './pages/Reports'

function AppRoutes(): React.ReactElement {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <Navigate to="/identities" replace />
          </RequireAuth>
        }
      />
      <Route
        path="/identities"
        element={
          <RequireAuth>
            <Identities />
          </RequireAuth>
        }
      />
      <Route
        path="/identities/:id"
        element={
          <RequireAuth>
            <IdentityDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/connectors"
        element={
          <RequireAuth>
            <Connectors />
          </RequireAuth>
        }
      />
      <Route
        path="/connectors/:id"
        element={
          <RequireAuth>
            <ConnectorDetail />
          </RequireAuth>
        }
      />
      <Route
        path="/enclaves"
        element={
          <RequireAuth>
            <Enclaves />
          </RequireAuth>
        }
      />
      <Route
        path="/reports"
        element={
          <RequireAuth>
            <Reports />
          </RequireAuth>
        }
      />
      <Route
        path="/users"
        element={
          <RequireAuth requireAdmin>
            <Users />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App(): React.ReactElement {
  return (
    <AuthProvider>
      <AppShell />
      <main className="main-content">
        <AppRoutes />
      </main>
    </AuthProvider>
  )
}
