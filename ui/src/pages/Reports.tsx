import React, { useState, useEffect, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import * as api from '../api/client'

function riskClass(score: number | null | undefined): string {
  if (score == null) return ''
  if (score >= 70) return 'risk-high'
  if (score >= 40) return 'risk-medium'
  return 'risk-low'
}

function daysUntilClass(days: number | null | undefined): string {
  if (days == null) return ''
  if (days < 30) return 'risk-high'
  if (days < 90) return 'risk-medium'
  return 'risk-low'
}

function daysUntil(dateStr: string | undefined | null): number | null {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - new Date().getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

export default function Reports(): React.ReactElement {
  const navigate = useNavigate()

  // Expiring certs state
  const [expiringDays, setExpiringDays] = useState<number>(90)
  const [expiringCerts, setExpiringCerts] = useState<api.Identity[]>([])
  const [expiringLoading, setExpiringLoading] = useState<boolean>(false)
  const [expiringError, setExpiringError] = useState<string>('')

  // Orphaned identities state
  const [orphaned, setOrphaned] = useState<api.Identity[]>([])
  const [orphanedLoading, setOrphanedLoading] = useState<boolean>(false)
  const [orphanedError, setOrphanedError] = useState<string>('')

  const fetchExpiring = async (days: number): Promise<void> => {
    setExpiringLoading(true)
    setExpiringError('')
    try {
      const res = await api.getExpiringReport(days)
      setExpiringCerts(Array.isArray(res.data) ? res.data : (res.data as api.PaginatedResponse<api.Identity>).items || [])
    } catch {
      setExpiringError('Failed to load expiring certificates report.')
    } finally {
      setExpiringLoading(false)
    }
  }

  const fetchOrphaned = async (): Promise<void> => {
    setOrphanedLoading(true)
    setOrphanedError('')
    try {
      const res = await api.getOrphanedReport()
      setOrphaned(Array.isArray(res.data) ? res.data : (res.data as api.PaginatedResponse<api.Identity>).items || [])
    } catch {
      setOrphanedError('Failed to load orphaned identities report.')
    } finally {
      setOrphanedLoading(false)
    }
  }

  useEffect(() => {
    fetchExpiring(expiringDays)
    fetchOrphaned()
  }, [])

  const handleDaysChange = (e: ChangeEvent<HTMLSelectElement>): void => {
    const days = Number(e.target.value)
    setExpiringDays(days)
    fetchExpiring(days)
  }

  return (
    <div>
      {/* Expiring Certificates */}
      <div className="card">
        <div className="card-header">
          <h2>Expiring Certificates</h2>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <label style={{ fontSize: '0.85rem', color: '#666', margin: 0 }}>Expiring within</label>
            <select
              value={expiringDays}
              onChange={handleDaysChange}
              style={{ width: 'auto', padding: '0.3rem 0.5rem', fontSize: '0.85rem' }}
            >
              <option value={30}>30 days</option>
              <option value={60}>60 days</option>
              <option value={90}>90 days</option>
              <option value={180}>180 days</option>
            </select>
          </div>
        </div>

        {expiringError && <div className="error-msg">{expiringError}</div>}

        {expiringLoading ? (
          <div className="loading">Loading expiring certificates...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Enclave</th>
                <th>Expiration</th>
                <th>Days Remaining</th>
                <th>Risk Score</th>
              </tr>
            </thead>
            <tbody>
              {expiringCerts.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: '#999' }}>No expiring certificates found.</td></tr>
              ) : (
                expiringCerts.map((cert) => {
                  const nd = (cert.normalized_data || {}) as Record<string, unknown>
                  const expDate = cert.not_after || (nd.not_after as string)
                  const days = daysUntil(expDate)
                  return (
                    <tr
                      key={cert.id}
                      className="clickable"
                      onClick={() => navigate(`/identities/${cert.id}`)}
                    >
                      <td><strong>{cert.display_name || (nd.display_name as string) || '--'}</strong></td>
                      <td>{cert.enclave_name || cert.enclave_id || '--'}</td>
                      <td>{expDate ? new Date(expDate).toLocaleDateString() : '--'}</td>
                      <td>
                        <span className={daysUntilClass(days)}>
                          {days != null ? (days > 0 ? `${days} days` : 'EXPIRED') : '--'}
                        </span>
                      </td>
                      <td>
                        <span className={riskClass(cert.risk_score)}>
                          {cert.risk_score != null ? cert.risk_score : '--'}
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        )}
      </div>

      {/* Orphaned Identities */}
      <div className="card">
        <div className="card-header">
          <h2>Orphaned Identities</h2>
          <span style={{ fontSize: '0.85rem', color: '#666' }}>
            Identities missing an owner or linked system
          </span>
        </div>

        {orphanedError && <div className="error-msg">{orphanedError}</div>}

        {orphanedLoading ? (
          <div className="loading">Loading orphaned identities...</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Enclave</th>
                <th>Missing</th>
                <th>Risk Score</th>
              </tr>
            </thead>
            <tbody>
              {orphaned.length === 0 ? (
                <tr><td colSpan={5} style={{ textAlign: 'center', color: '#999' }}>No orphaned identities found.</td></tr>
              ) : (
                orphaned.map((ident) => {
                  const nd = (ident.normalized_data || {}) as Record<string, unknown>
                  const hasOwner = !!(ident.owner || nd.owner)
                  const hasLinked = !!(ident.linked_system || nd.linked_system)
                  const missing: string[] = []
                  if (!hasOwner) missing.push('Owner')
                  if (!hasLinked) missing.push('Linked System')
                  return (
                    <tr
                      key={ident.id}
                      className="clickable"
                      onClick={() => navigate(`/identities/${ident.id}`)}
                    >
                      <td><strong>{ident.display_name || (nd.display_name as string) || '--'}</strong></td>
                      <td>{ident.type || ident.identity_type || '--'}</td>
                      <td>{ident.enclave_name || ident.enclave_id || '--'}</td>
                      <td>
                        {missing.map((m) => (
                          <span key={m} className="badge badge-failed" style={{ marginRight: '0.3rem' }}>{m}</span>
                        ))}
                      </td>
                      <td>
                        <span className={riskClass(ident.risk_score)}>
                          {ident.risk_score != null ? ident.risk_score : '--'}
                        </span>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
