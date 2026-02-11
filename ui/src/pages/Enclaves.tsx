import React, { useState, useEffect, FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import * as api from '../api/client'

interface EnclaveForm {
  name: string
  description: string
}

interface AxiosErrorResponse {
  response?: {
    data?: {
      detail?: string
    }
  }
}

export default function Enclaves(): React.ReactElement {
  const { isAdmin } = useAuth()
  const [enclaves, setEnclaves] = useState<api.Enclave[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')
  const [showForm, setShowForm] = useState<boolean>(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<EnclaveForm>({ name: '', description: '' })

  const fetchEnclaves = async (): Promise<void> => {
    setLoading(true)
    try {
      const res = await api.getEnclaves()
      setEnclaves(Array.isArray(res.data) ? res.data : (res.data as api.PaginatedResponse<api.Enclave>).items || [])
    } catch {
      setError('Failed to load enclaves.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchEnclaves() }, [])

  const resetForm = (): void => {
    setForm({ name: '', description: '' })
    setEditingId(null)
    setShowForm(false)
  }

  const handleEdit = (enc: api.Enclave): void => {
    setForm({ name: enc.name, description: enc.description || '' })
    setEditingId(enc.id)
    setShowForm(true)
  }

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    try {
      if (editingId) {
        await api.updateEnclave(editingId, form)
      } else {
        await api.createEnclave(form)
      }
      resetForm()
      fetchEnclaves()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to save enclave.')
    }
  }

  const handleDelete = async (id: string): Promise<void> => {
    if (!window.confirm('Delete this enclave? This cannot be undone.')) return
    try {
      await api.deleteEnclave(id)
      fetchEnclaves()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to delete enclave.')
    }
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Enclaves</h2>
          {isAdmin && !showForm && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>
              + Add Enclave
            </button>
          )}
        </div>

        {error && <div className="error-msg">{error}</div>}

        {showForm && (
          <div className="inline-form">
            <h3>{editingId ? 'Edit Enclave' : 'New Enclave'}</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Name</label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  required
                />
              </div>
              <div className="form-group">
                <label>Description</label>
                <input
                  type="text"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>
              <div className="btn-group">
                <button type="submit" className="btn btn-primary btn-sm">
                  {editingId ? 'Update' : 'Create'}
                </button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={resetForm}>
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading enclaves...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Description</th>
                <th>Created</th>
                {isAdmin && <th>Actions</th>}
              </tr>
            </thead>
            <tbody>
              {enclaves.length === 0 ? (
                <tr><td colSpan={isAdmin ? 4 : 3} style={{ textAlign: 'center', color: '#999' }}>No enclaves found.</td></tr>
              ) : (
                enclaves.map((enc) => (
                  <tr key={enc.id}>
                    <td><strong>{enc.name}</strong></td>
                    <td>{enc.description || '--'}</td>
                    <td>{enc.created_at ? new Date(enc.created_at).toLocaleDateString() : '--'}</td>
                    {isAdmin && (
                      <td>
                        <div className="btn-group">
                          <button className="btn btn-secondary btn-sm" onClick={() => handleEdit(enc)}>Edit</button>
                          <button className="btn btn-danger btn-sm" onClick={() => handleDelete(enc.id)}>Delete</button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
