import React, { useState, useEffect, FormEvent } from 'react'
import * as api from '../api/client'

interface UserForm {
  username: string
  password: string
  email: string
}

interface RoleForm {
  userId: string | null
  role_name: string
  enclave_id: string
}

interface AxiosErrorResponse {
  response?: {
    data?: {
      detail?: string
    }
  }
}

export default function Users(): React.ReactElement {
  const [users, setUsers] = useState<api.User[]>([])
  const [enclaves, setEnclaves] = useState<api.Enclave[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [showCreateUser, setShowCreateUser] = useState<boolean>(false)
  const [userForm, setUserForm] = useState<UserForm>({ username: '', password: '', email: '' })
  const [roleForm, setRoleForm] = useState<RoleForm>({ userId: null, role_name: '', enclave_id: '' })

  const fetchData = async (): Promise<void> => {
    setLoading(true)
    try {
      const [usersRes, enclavesRes] = await Promise.all([api.getUsers(), api.getEnclaves()])
      setUsers(Array.isArray(usersRes.data) ? usersRes.data : (usersRes.data as api.PaginatedResponse<api.User>).items || [])
      setEnclaves(Array.isArray(enclavesRes.data) ? enclavesRes.data : (enclavesRes.data as api.PaginatedResponse<api.Enclave>).items || [])
    } catch {
      setError('Failed to load data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const clearMessages = (): void => { setError(''); setSuccess('') }

  const handleCreateUser = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    clearMessages()
    try {
      await api.createUser(userForm)
      setUserForm({ username: '', password: '', email: '' })
      setShowCreateUser(false)
      setSuccess('User created.')
      fetchData()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to create user.')
    }
  }

  const handleDeleteUser = async (id: string): Promise<void> => {
    if (!window.confirm('Delete this user?')) return
    clearMessages()
    try {
      await api.deleteUser(id)
      fetchData()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to delete user.')
    }
  }

  const handleAssignRole = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    clearMessages()
    try {
      await api.assignRole(roleForm.userId!, {
        role_name: roleForm.role_name,
        enclave_id: roleForm.enclave_id || undefined,
      })
      setRoleForm({ userId: null, role_name: '', enclave_id: '' })
      setSuccess('Role assigned.')
      fetchData()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to assign role.')
    }
  }

  const handleRemoveRole = async (userId: string, roleEnclaveId: string): Promise<void> => {
    clearMessages()
    try {
      await api.removeRole(userId, roleEnclaveId)
      fetchData()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to remove role.')
    }
  }

  if (loading) return <div className="loading">Loading users...</div>

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Users</h2>
          {!showCreateUser && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowCreateUser(true)}>
              + Add User
            </button>
          )}
        </div>

        {error && <div className="error-msg">{error}</div>}
        {success && <div className="success-msg">{success}</div>}

        {showCreateUser && (
          <div className="inline-form">
            <h3>Create User</h3>
            <form onSubmit={handleCreateUser}>
              <div className="form-group">
                <label>Username</label>
                <input
                  type="text"
                  value={userForm.username}
                  onChange={(e) => setUserForm({ ...userForm, username: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Password</label>
                <input
                  type="password"
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Email</label>
                <input
                  type="email"
                  value={userForm.email}
                  onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                />
              </div>
              <div className="btn-group">
                <button type="submit" className="btn btn-primary btn-sm">Create</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowCreateUser(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        <table>
          <thead>
            <tr>
              <th>Username</th>
              <th>Email</th>
              <th>Roles</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.length === 0 ? (
              <tr><td colSpan={4} style={{ textAlign: 'center', color: '#999' }}>No users found.</td></tr>
            ) : (
              users.map((u) => (
                <tr key={u.id}>
                  <td><strong>{u.username}</strong></td>
                  <td>{u.email || '--'}</td>
                  <td>
                    {u.role_assignments && u.role_assignments.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem' }}>
                        {u.role_assignments.map((ra) => (
                          <span key={ra.id} className="badge badge-info" style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                            {ra.role_name}{ra.enclave_name ? ` @ ${ra.enclave_name}` : ''}
                            <button
                              onClick={() => handleRemoveRole(u.id, ra.id)}
                              style={{
                                background: 'none', border: 'none', cursor: 'pointer',
                                color: '#004085', fontWeight: 'bold', fontSize: '0.85rem', padding: 0,
                              }}
                              title="Remove role"
                            >
                              x
                            </button>
                          </span>
                        ))}
                      </div>
                    ) : (
                      <span style={{ color: '#999' }}>None</span>
                    )}
                  </td>
                  <td>
                    <div className="btn-group">
                      <button
                        className="btn btn-success btn-sm"
                        onClick={() => setRoleForm({ ...roleForm, userId: u.id })}
                      >
                        + Role
                      </button>
                      <button className="btn btn-danger btn-sm" onClick={() => handleDeleteUser(u.id)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {roleForm.userId && (
        <div className="card">
          <div className="card-header">
            <h2>Assign Role to {users.find((u) => u.id === roleForm.userId)?.username}</h2>
          </div>
          <form onSubmit={handleAssignRole}>
            <div className="filter-bar">
              <div className="form-group">
                <label>Role</label>
                <select
                  value={roleForm.role_name}
                  onChange={(e) => setRoleForm({ ...roleForm, role_name: e.target.value })}
                  required
                >
                  <option value="">Select role...</option>
                  <option value="admin">admin</option>
                  <option value="analyst">analyst</option>
                  <option value="viewer">viewer</option>
                </select>
              </div>
              <div className="form-group">
                <label>Enclave (optional)</label>
                <select
                  value={roleForm.enclave_id}
                  onChange={(e) => setRoleForm({ ...roleForm, enclave_id: e.target.value })}
                >
                  <option value="">Global</option>
                  {enclaves.map((enc) => (
                    <option key={enc.id} value={enc.id}>{enc.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem' }}>
                <button type="submit" className="btn btn-primary btn-sm">Assign</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setRoleForm({ userId: null, role_name: '', enclave_id: '' })}>Cancel</button>
              </div>
            </div>
          </form>
        </div>
      )}
    </div>
  )
}
