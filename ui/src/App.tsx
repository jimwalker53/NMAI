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
import Settings from './pages/Settings'

export default function App(): React.ReactElement {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<RequireAuth><AppShell /></RequireAuth>}>
          <Route index element={<Navigate to="/identities" replace />} />
          <Route path="identities" element={<Identities />} />
          <Route path="identities/:id" element={<IdentityDetail />} />
          <Route path="connectors" element={<Connectors />} />
          <Route path="connectors/:id" element={<ConnectorDetail />} />
          <Route path="enclaves" element={<Enclaves />} />
          <Route path="reports" element={<Reports />} />
          <Route path="users" element={<Users />} />
          <Route path="settings" element={<Settings />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
