import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function AppShell(): React.ReactElement | null {
  const { isAuthenticated, isAdmin, user, logout } = useAuth()
  const location = useLocation()

  if (!isAuthenticated || location.pathname === '/login') {
    return null
  }

  return (
    <nav className="navbar">
      <div className="navbar-brand">NMIA</div>
      <div className="navbar-links">
        <NavLink to="/identities" className={({ isActive }) => isActive ? 'active' : ''}>
          Identities
        </NavLink>
        <NavLink to="/connectors" className={({ isActive }) => isActive ? 'active' : ''}>
          Connectors
        </NavLink>
        <NavLink to="/enclaves" className={({ isActive }) => isActive ? 'active' : ''}>
          Enclaves
        </NavLink>
        <NavLink to="/reports" className={({ isActive }) => isActive ? 'active' : ''}>
          Reports
        </NavLink>
        {isAdmin && (
          <NavLink to="/users" className={({ isActive }) => isActive ? 'active' : ''}>
            Users
          </NavLink>
        )}
      </div>
      <div className="navbar-right">
        <span className="navbar-user">{user?.sub || user?.username || 'User'}</span>
        <button className="btn-logout" onClick={logout}>Logout</button>
      </div>
    </nav>
  )
}
