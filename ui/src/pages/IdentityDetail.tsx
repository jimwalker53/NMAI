import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import * as api from '../api/client'

interface AxiosErrorResponse {
  response?: {
    data?: {
      detail?: string
    }
  }
}

function riskClass(score: number | null | undefined): string {
  if (score == null) return ''
  if (score >= 70) return 'risk-high'
  if (score >= 40) return 'risk-medium'
  return 'risk-low'
}

function daysUntil(dateStr: string | undefined | null): number | null {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - new Date().getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

function formatValue(val: unknown): string {
  if (val == null) return '--'
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return String(val)
}

/** Fields that should not be displayed in the raw kv-table (handled specially) */
const SPECIAL_FIELDS = new Set(['owner', 'linked_system', 'sans', 'not_after', 'not_before', 'finding_ids'])

export default function IdentityDetail(): React.ReactElement {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [identity, setIdentity] = useState<api.Identity | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')
  const [success, setSuccess] = useState<string>('')
  const [owner, setOwner] = useState<string>('')
  const [linkedSystem, setLinkedSystem] = useState<string>('')
  const [saving, setSaving] = useState<boolean>(false)

  const fetchIdentity = async (): Promise<void> => {
    setLoading(true)
    try {
      const res = await api.getIdentity(id!)
      setIdentity(res.data)
      const nd = (res.data.normalized_data || res.data) as Record<string, unknown>
      setOwner((nd.owner as string) || res.data.owner || '')
      setLinkedSystem((nd.linked_system as string) || res.data.linked_system || '')
    } catch {
      setError('Failed to load identity.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchIdentity() }, [id])

  const handleSave = async (): Promise<void> => {
    setError('')
    setSuccess('')
    setSaving(true)
    try {
      await api.updateIdentity(id!, { owner, linked_system: linkedSystem })
      setSuccess('Identity updated.')
      fetchIdentity()
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      setError(axiosErr.response?.data?.detail || 'Failed to update identity.')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="loading">Loading identity...</div>
  if (!identity) return <div className="error-msg">Identity not found.</div>

  const nd = (identity.normalized_data || {}) as Record<string, unknown>
  const isCert = identity.type === 'cert' || identity.identity_type === 'cert'
  const expiry = (nd.not_after as string) || identity.not_after
  const daysLeft = daysUntil(expiry)
  const sans: (string | unknown)[] = (nd.sans as string[]) || identity.sans || []
  const findingIds: (api.FindingRef | string)[] = (nd.finding_ids as api.FindingRef[]) || identity.finding_ids || []

  // Build key-value pairs from normalized_data, excluding special fields
  const kvPairs = Object.entries(nd).filter(([k]) => !SPECIAL_FIELDS.has(k))

  // Risk breakdown: attempt to show contributing factors
  const riskFactors = identity.risk_factors || identity.risk_breakdown || (nd.risk_factors as api.RiskFactor[] | Record<string, unknown> | undefined) || null

  return (
    <div>
      <div className="detail-header">
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => navigate('/identities')}
          style={{ marginBottom: '0.75rem' }}
        >
          &larr; Back to Identities
        </button>
        <h1>{(nd.display_name as string) || identity.display_name || 'Identity'}</h1>
        <div className="detail-meta">
          <span>Type: <strong>{identity.type || identity.identity_type || '--'}</strong></span>
          <span>Enclave: <strong>{identity.enclave_name || identity.enclave_id || '--'}</strong></span>
          <span>
            Risk Score:{' '}
            <span className={riskClass(identity.risk_score)}>
              {identity.risk_score != null ? identity.risk_score : '--'}
            </span>
          </span>
        </div>
      </div>

      {error && <div className="error-msg">{error}</div>}
      {success && <div className="success-msg">{success}</div>}

      {/* Editable fields */}
      <div className="card">
        <div className="card-header">
          <h2>Ownership</h2>
        </div>
        <div className="filter-bar">
          <div className="form-group">
            <label>Owner</label>
            <input
              type="text"
              value={owner}
              onChange={(e) => setOwner(e.target.value)}
              placeholder="Assign an owner..."
            />
          </div>
          <div className="form-group">
            <label>Linked System</label>
            <input
              type="text"
              value={linkedSystem}
              onChange={(e) => setLinkedSystem(e.target.value)}
              placeholder="e.g. Jenkins, Terraform..."
            />
          </div>
          <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving}>
              {saving ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>

      {/* Certificate-specific info */}
      {isCert && (
        <div className="card">
          <div className="card-header">
            <h2>Certificate Details</h2>
          </div>
          {expiry && (
            <div style={{ marginBottom: '1rem' }}>
              <strong>Expiration:</strong>{' '}
              {new Date(expiry).toLocaleDateString()}{' '}
              {daysLeft != null && (
                <span className={daysLeft < 30 ? 'risk-high' : daysLeft < 90 ? 'risk-medium' : 'risk-low'}>
                  ({daysLeft > 0 ? `${daysLeft} days remaining` : 'EXPIRED'})
                </span>
              )}
            </div>
          )}
          {(nd.not_before as string) && (
            <div style={{ marginBottom: '1rem' }}>
              <strong>Not Before:</strong> {new Date(nd.not_before as string).toLocaleDateString()}
            </div>
          )}
          {sans.length > 0 && (
            <div>
              <strong>Subject Alternative Names:</strong>
              <ul style={{ marginTop: '0.25rem', paddingLeft: '1.5rem' }}>
                {(Array.isArray(sans) ? sans : [sans]).map((san, idx) => (
                  <li key={idx} style={{ fontSize: '0.875rem' }}>{String(san)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Risk Score */}
      <div className="card">
        <div className="card-header">
          <h2>Risk Assessment</h2>
        </div>
        <div style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>
          <span className={riskClass(identity.risk_score)}>
            {identity.risk_score != null ? identity.risk_score : '--'}
          </span>
          <span style={{ fontSize: '0.9rem', color: '#666', marginLeft: '0.5rem' }}>/ 100</span>
        </div>
        {riskFactors ? (
          <div>
            <strong>Contributing Factors:</strong>
            {Array.isArray(riskFactors) ? (
              <ul style={{ paddingLeft: '1.5rem', marginTop: '0.25rem' }}>
                {(riskFactors as api.RiskFactor[]).map((f, idx) => (
                  <li key={idx} style={{ fontSize: '0.85rem' }}>
                    {typeof f === 'string' ? f : `${f.factor || f.name}: +${f.score || f.weight}`}
                  </li>
                ))}
              </ul>
            ) : typeof riskFactors === 'object' ? (
              <table className="kv-table" style={{ marginTop: '0.5rem' }}>
                <tbody>
                  {Object.entries(riskFactors as Record<string, unknown>).map(([k, v]) => (
                    <tr key={k}>
                      <th>{k}</th>
                      <td>{formatValue(v)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ fontSize: '0.85rem' }}>{String(riskFactors)}</p>
            )}
          </div>
        ) : (
          <p style={{ fontSize: '0.85rem', color: '#666' }}>
            Risk score factors are computed based on: missing owner, missing linked system,
            certificate expiration proximity, stale last-seen date, and elevated privileges.
          </p>
        )}
      </div>

      {/* Normalized Data */}
      <div className="card">
        <div className="card-header">
          <h2>Normalized Data</h2>
        </div>
        {kvPairs.length === 0 ? (
          <p style={{ color: '#999', fontSize: '0.85rem' }}>No additional data fields.</p>
        ) : (
          <table className="kv-table">
            <tbody>
              {kvPairs.map(([key, val]) => (
                <tr key={key}>
                  <th>{key}</th>
                  <td>
                    {typeof val === 'object' && val !== null ? (
                      <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: '0.8rem' }}>
                        {JSON.stringify(val, null, 2)}
                      </pre>
                    ) : (
                      formatValue(val)
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Provenance */}
      {findingIds.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2>Provenance</h2>
          </div>
          <table>
            <thead>
              <tr>
                <th>Finding ID</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {findingIds.map((f, idx) => {
                const fid = typeof f === 'object' ? (f as api.FindingRef).id || (f as api.FindingRef).finding_id : f
                const ts = typeof f === 'object' ? (f as api.FindingRef).timestamp || (f as api.FindingRef).created_at : null
                return (
                  <tr key={idx}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{fid}</td>
                    <td>{ts ? new Date(ts).toLocaleString() : '--'}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
