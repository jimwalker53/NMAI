import React, { useState, useEffect, useRef, useCallback, ChangeEvent } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as api from '../api/client'

interface AxiosErrorResponse {
  response?: {
    data?: {
      detail?: string
    }
  }
}

/** Simple cron-to-human-readable helper */
function describeCron(expr: string): string {
  if (!expr) return 'Not scheduled'
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return expr
  const [min, hr, dom, mon, dow] = parts
  if (min === '0' && hr !== '*' && dom === '*' && mon === '*' && dow === '*') {
    return `Daily at ${hr.padStart(2, '0')}:00`
  }
  if (min !== '*' && hr !== '*' && dom === '*' && mon === '*' && dow !== '*') {
    const days: Record<string, string> = { 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat' }
    return `${days[dow] || dow} at ${hr.padStart(2, '0')}:${min.padStart(2, '0')}`
  }
  if (min === '*' && hr === '*' && dom === '*' && mon === '*' && dow === '*') {
    return 'Every minute'
  }
  if (min.startsWith('*/')) {
    return `Every ${min.slice(2)} minutes`
  }
  return expr
}

export default function ConnectorDetail(): React.ReactElement {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [connector, setConnector] = useState<api.Connector | null>(null)
  const [jobs, setJobs] = useState<api.ConnectorJob[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [configText, setConfigText] = useState<string>('{}')
  const [cronText, setCronText] = useState<string>('')
  const [saving, setSaving] = useState<boolean>(false)
  const [testing, setTesting] = useState<boolean>(false)
  const [testResult, setTestResult] = useState<api.TestResult | null>(null)
  const [running, setRunning] = useState<boolean>(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState<boolean>(false)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchConnector = useCallback(async (): Promise<void> => {
    try {
      const res = await api.getConnector(id!)
      const data = res.data
      if (!data) {
        setError('Connector not found.')
        setLoading(false)
        return
      }
      setConnector(data)
      setConfigText(JSON.stringify(data.config || {}, null, 2))
      setCronText(data.cron_expression || '')
    } catch {
      setError('Failed to load connector.')
    } finally {
      setLoading(false)
    }
  }, [id])

  const fetchJobs = useCallback(async (): Promise<api.ConnectorJob[]> => {
    try {
      const res = await api.getConnectorJobs(id!)
      const jobList = Array.isArray(res.data) ? res.data : (res.data as api.PaginatedResponse<api.ConnectorJob>).items || []
      setJobs(jobList)
      return jobList
    } catch {
      // Jobs endpoint may not exist yet
      return []
    }
  }, [id])

  const stopPolling = useCallback((): void => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const startPolling = useCallback((): void => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      const jobList = await fetchJobs()
      if (!jobList.some((j) => j.status === 'running' || j.status === 'queued')) {
        stopPolling()
        fetchConnector()
      }
    }, 3000)
  }, [fetchJobs, fetchConnector, stopPolling])

  useEffect(() => {
    const init = async (): Promise<void> => {
      await fetchConnector()
      const jobList = await fetchJobs()
      if (jobList.some((j) => j.status === 'running' || j.status === 'queued')) {
        startPolling()
      }
    }
    init()
    return () => stopPolling()
  }, [fetchConnector, fetchJobs, startPolling, stopPolling])

  const handleSaveConfig = async (): Promise<void> => {
    setError('')
    setSuccess('')
    setSaving(true)
    try {
      let parsedConfig: Record<string, unknown>
      try {
        parsedConfig = JSON.parse(configText)
      } catch {
        setError('Config must be valid JSON.')
        setSaving(false)
        return
      }
      await api.updateConnector(id!, {
        config: parsedConfig,
        cron_expression: cronText || undefined,
      })
      setSuccess('Connector updated.')
      fetchConnector()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to update connector.')
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async (): Promise<void> => {
    setTestResult(null)
    setTesting(true)
    setError('')
    try {
      const res = await api.testConnector(id!)
      setTestResult(res.data)
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setTestResult({ success: false, error: axiosErr.response?.data?.detail || 'Test failed.' })
    } finally {
      setTesting(false)
    }
  }

  const handleRun = async (): Promise<void> => {
    setError('')
    setSuccess('')
    setRunning(true)
    try {
      await api.runConnector(id!)
      setSuccess('Connector run started.')
      startPolling()
      fetchJobs()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to start connector run.')
    } finally {
      setRunning(false)
    }
  }

  const handleToggleEnabled = async (): Promise<void> => {
    setError('')
    try {
      await api.updateConnector(id!, { enabled: !connector!.enabled })
      fetchConnector()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to toggle connector.')
    }
  }

  const handleUpload = async (): Promise<void> => {
    if (!selectedFile) return
    setError('')
    setSuccess('')
    setUploading(true)
    try {
      const res = await api.uploadCSV(id!, selectedFile)
      setSuccess(`Upload complete. ${res.data.records_ingested ?? 'Records'} ingested.`)
      setSelectedFile(null)
      fetchJobs()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (): Promise<void> => {
    if (!window.confirm('Delete this connector? This cannot be undone.')) return
    try {
      await api.deleteConnector(id!)
      navigate('/connectors', { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to delete connector.')
    }
  }

  const jobBadge = (status: string): string => {
    const map: Record<string, string> = {
      completed: 'badge-completed',
      success: 'badge-success',
      failed: 'badge-failed',
      error: 'badge-error',
      running: 'badge-running',
      queued: 'badge-queued',
      pending: 'badge-pending',
    }
    return `badge ${map[status] || 'badge-info'}`
  }

  if (loading) return <div className="loading">Loading connector...</div>
  if (!connector) return <div className="error-msg">Connector not found.</div>

  const isFileType = connector.connector_type === 'adcs_file' || connector.connector_type === 'csv_file'

  return (
    <div>
      {/* Header */}
      <div className="detail-header">
        <h1>{connector.name}</h1>
        <div className="detail-meta">
          <span>Type: <strong>{connector.connector_type}</strong></span>
          <span>Enclave: <strong>{connector.enclave_name || connector.enclave_id}</strong></span>
          <span>
            Status:{' '}
            <span className={connector.enabled ? 'badge badge-active' : 'badge badge-disabled'}>
              {connector.enabled ? 'Enabled' : 'Disabled'}
            </span>
          </span>
        </div>
      </div>

      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}

      {/* Actions */}
      <div className="card">
        <div className="card-header">
          <h2>Actions</h2>
        </div>
        <div className="btn-group">
          <button className="btn btn-primary" onClick={handleTest} disabled={testing}>
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
          <button className="btn btn-success" onClick={handleRun} disabled={running}>
            {running ? 'Starting...' : 'Run Now'}
          </button>
          <button className="btn btn-warning" onClick={handleToggleEnabled}>
            {connector.enabled ? 'Disable' : 'Enable'}
          </button>
          <button className="btn btn-danger" onClick={handleDelete}>Delete</button>
        </div>
        {testResult && (
          <div style={{ marginTop: '1rem' }}>
            {testResult.success ? (
              <div className="success-msg">Connection test passed. {testResult.message || ''}</div>
            ) : (
              <div className="error-msg">Connection test failed: {testResult.error || 'Unknown error'}</div>
            )}
          </div>
        )}
      </div>

      {/* Config */}
      <div className="card">
        <div className="card-header">
          <h2>Configuration</h2>
        </div>
        <div className="form-group">
          <label>Config (JSON)</label>
          <textarea
            value={configText}
            onChange={(e) => setConfigText(e.target.value)}
            rows={8}
          />
        </div>
        <div className="form-group">
          <label>Cron Expression</label>
          <input
            type="text"
            value={cronText}
            onChange={(e) => setCronText(e.target.value)}
            placeholder="e.g. 0 2 * * *"
          />
          <small style={{ color: '#666', fontSize: '0.8rem' }}>
            Schedule: {describeCron(cronText)}
          </small>
        </div>
        <button className="btn btn-primary btn-sm" onClick={handleSaveConfig} disabled={saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </div>

      {/* File Upload (for adcs_file / csv_file types) */}
      {isFileType && (
        <div className="card">
          <div className="card-header">
            <h2>File Upload</h2>
          </div>
          <p style={{ marginBottom: '1rem', fontSize: '0.85rem', color: '#666' }}>
            Upload a CSV file to ingest identities for this connector.
          </p>
          <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
            <input
              type="file"
              accept=".csv,.tsv,.txt"
              onChange={(e: ChangeEvent<HTMLInputElement>) => setSelectedFile(e.target.files?.[0] || null)}
            />
            <button
              className="btn btn-primary btn-sm"
              onClick={handleUpload}
              disabled={!selectedFile || uploading}
            >
              {uploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>
      )}

      {/* Job History */}
      <div className="card">
        <div className="card-header">
          <h2>Job History</h2>
          <button className="btn btn-secondary btn-sm" onClick={() => { fetchJobs() }}>Refresh</button>
        </div>
        {jobs.length === 0 ? (
          <p style={{ color: '#999', fontSize: '0.85rem' }}>No jobs recorded yet.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Status</th>
                <th>Started</th>
                <th>Finished</th>
                <th>Found</th>
                <th>Ingested</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((j, idx) => (
                <tr key={j.id || idx}>
                  <td><span className={jobBadge(j.status)}>{j.status}</span></td>
                  <td>{j.started_at ? new Date(j.started_at).toLocaleString() : '--'}</td>
                  <td>{j.finished_at ? new Date(j.finished_at).toLocaleString() : '--'}</td>
                  <td>{j.records_found ?? '--'}</td>
                  <td>{j.records_ingested ?? '--'}</td>
                  <td style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {j.error || '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
