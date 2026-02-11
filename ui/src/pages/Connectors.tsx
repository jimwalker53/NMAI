import React, { useState, useEffect, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import * as api from '../api/client'

interface ConnectorForm {
  name: string
  connector_type: string
  enclave_id: string
  config: string
  cron_expression: string
}

interface AxiosErrorResponse {
  response?: {
    data?: {
      detail?: string
    }
  }
}

export default function Connectors(): React.ReactElement {
  const navigate = useNavigate()
  const [connectors, setConnectors] = useState<api.Connector[]>([])
  const [connectorTypes, setConnectorTypes] = useState<(string | api.ConnectorType)[]>([])
  const [enclaves, setEnclaves] = useState<api.Enclave[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')
  const [showForm, setShowForm] = useState<boolean>(false)
  const [form, setForm] = useState<ConnectorForm>({
    name: '',
    connector_type: '',
    enclave_id: '',
    config: '{}',
    cron_expression: '',
  })

  const fetchData = async (): Promise<void> => {
    setLoading(true)
    try {
      const [cRes, tRes, eRes] = await Promise.all([
        api.getConnectors(),
        api.getConnectorTypes(),
        api.getEnclaves(),
      ])
      setConnectors(Array.isArray(cRes.data) ? cRes.data : (cRes.data as api.PaginatedResponse<api.Connector>).items || [])
      setConnectorTypes(Array.isArray(tRes.data) ? tRes.data : (tRes.data as { types: (string | api.ConnectorType)[] }).types || [])
      setEnclaves(Array.isArray(eRes.data) ? eRes.data : (eRes.data as api.PaginatedResponse<api.Enclave>).items || [])
    } catch {
      setError('Failed to load connectors.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchData() }, [])

  const handleSubmit = async (e: FormEvent<HTMLFormElement>): Promise<void> => {
    e.preventDefault()
    setError('')
    try {
      let parsedConfig: Record<string, unknown>
      try {
        parsedConfig = JSON.parse(form.config)
      } catch {
        setError('Config must be valid JSON.')
        return
      }
      await api.createConnector({
        name: form.name,
        connector_type: form.connector_type,
        enclave_id: form.enclave_id,
        config: parsedConfig,
        cron_expression: form.cron_expression || null,
      })
      setShowForm(false)
      setForm({ name: '', connector_type: '', enclave_id: '', config: '{}', cron_expression: '' })
      fetchData()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to create connector.')
    }
  }

  const badgeClass = (connector: api.Connector): string => {
    if (!connector.enabled) return 'badge badge-disabled'
    return 'badge badge-active'
  }

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Connectors</h2>
          {!showForm && (
            <button className="btn btn-primary btn-sm" onClick={() => setShowForm(true)}>
              + Add Connector
            </button>
          )}
        </div>

        {error && <div className="error-msg">{error}</div>}

        {showForm && (
          <div className="inline-form">
            <h3>New Connector</h3>
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
                <label>Type</label>
                <select
                  value={form.connector_type}
                  onChange={(e) => setForm({ ...form, connector_type: e.target.value })}
                  required
                >
                  <option value="">Select type...</option>
                  {connectorTypes.map((t) => {
                    const val = typeof t === 'string' ? t : t.name || t.id || ''
                    const label = typeof t === 'string' ? t : t.label || t.name || t.id || ''
                    return <option key={val} value={val}>{label}</option>
                  })}
                </select>
              </div>
              <div className="form-group">
                <label>Enclave</label>
                <select
                  value={form.enclave_id}
                  onChange={(e) => setForm({ ...form, enclave_id: e.target.value })}
                  required
                >
                  <option value="">Select enclave...</option>
                  {enclaves.map((enc) => (
                    <option key={enc.id} value={enc.id}>{enc.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Config (JSON)</label>
                <textarea
                  value={form.config}
                  onChange={(e) => setForm({ ...form, config: e.target.value })}
                  rows={5}
                />
              </div>
              <div className="form-group">
                <label>Cron Expression</label>
                <input
                  type="text"
                  value={form.cron_expression}
                  onChange={(e) => setForm({ ...form, cron_expression: e.target.value })}
                  placeholder="e.g. 0 2 * * *"
                />
              </div>
              <div className="btn-group">
                <button type="submit" className="btn btn-primary btn-sm">Create</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setShowForm(false)}>Cancel</button>
              </div>
            </form>
          </div>
        )}

        {loading ? (
          <div className="loading">Loading connectors...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Enclave</th>
                <th>Cron</th>
                <th>Status</th>
                <th>Last Run</th>
              </tr>
            </thead>
            <tbody>
              {connectors.length === 0 ? (
                <tr><td colSpan={6} style={{ textAlign: 'center', color: '#999' }}>No connectors configured.</td></tr>
              ) : (
                connectors.map((c) => (
                  <tr key={c.id} className="clickable" onClick={() => navigate(`/connectors/${c.id}`)}>
                    <td><strong>{c.name}</strong></td>
                    <td>{c.connector_type}</td>
                    <td>{c.enclave_name || c.enclave_id || '--'}</td>
                    <td><code>{c.cron_expression || '--'}</code></td>
                    <td>
                      <span className={badgeClass(c)}>
                        {c.enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </td>
                    <td>{c.last_run_at ? new Date(c.last_run_at).toLocaleString() : '--'}</td>
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
