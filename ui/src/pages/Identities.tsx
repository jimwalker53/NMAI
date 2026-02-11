import React, { useState, useEffect, useCallback, KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import * as api from '../api/client'

function riskClass(score: number | null | undefined): string {
  if (score == null) return ''
  if (score >= 70) return 'risk-high'
  if (score >= 40) return 'risk-medium'
  return 'risk-low'
}

const PAGE_SIZE = 25

export default function Identities(): React.ReactElement {
  const navigate = useNavigate()
  const [identities, setIdentities] = useState<api.Identity[]>([])
  const [enclaves, setEnclaves] = useState<api.Enclave[]>([])
  const [total, setTotal] = useState<number>(0)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string>('')

  // Filters
  const [enclaveFilter, setEnclaveFilter] = useState<string>('')
  const [typeFilter, setTypeFilter] = useState<string>('')
  const [search, setSearch] = useState<string>('')
  const [riskMin, setRiskMin] = useState<string>('')
  const [riskMax, setRiskMax] = useState<string>('')
  const [offset, setOffset] = useState<number>(0)

  const fetchIdentities = useCallback(async (): Promise<void> => {
    setLoading(true)
    setError('')
    try {
      const params: api.IdentityQueryParams = { limit: PAGE_SIZE, offset }
      if (enclaveFilter) params.enclave_id = enclaveFilter
      if (typeFilter) params.type = typeFilter
      if (search) params.search = search
      if (riskMin !== '') params.risk_score_min = Number(riskMin)
      if (riskMax !== '') params.risk_score_max = Number(riskMax)
      const res = await api.getIdentities(params)
      if (Array.isArray(res.data)) {
        setIdentities(res.data)
        setTotal(res.data.length)
      } else {
        const paginated = res.data as api.PaginatedResponse<api.Identity>
        setIdentities(paginated.items || [])
        setTotal(paginated.total ?? paginated.items?.length ?? 0)
      }
    } catch {
      setError('Failed to load identities.')
    } finally {
      setLoading(false)
    }
  }, [enclaveFilter, typeFilter, search, riskMin, riskMax, offset])

  useEffect(() => {
    api.getEnclaves().then((res) => {
      setEnclaves(Array.isArray(res.data) ? res.data : (res.data as api.PaginatedResponse<api.Enclave>).items || [])
    }).catch(() => {})
  }, [])

  useEffect(() => { fetchIdentities() }, [fetchIdentities])

  const handleFilterApply = (): void => {
    setOffset(0)
    fetchIdentities()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>): void => {
    if (e.key === 'Enter') handleFilterApply()
  }

  const hasNext = identities.length === PAGE_SIZE
  const hasPrev = offset > 0
  const page = Math.floor(offset / PAGE_SIZE) + 1

  return (
    <div>
      <div className="card">
        <div className="card-header">
          <h2>Identities</h2>
          <span style={{ color: '#666', fontSize: '0.85rem' }}>{total} total</span>
        </div>

        {/* Filter bar */}
        <div className="filter-bar">
          <div className="form-group">
            <label>Enclave</label>
            <select value={enclaveFilter} onChange={(e) => setEnclaveFilter(e.target.value)}>
              <option value="">All</option>
              {enclaves.map((enc) => (
                <option key={enc.id} value={enc.id}>{enc.name}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Type</label>
            <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)}>
              <option value="">All</option>
              <option value="svc_acct">Service Account</option>
              <option value="cert">Certificate</option>
              <option value="api_key">API Key</option>
              <option value="bot">Bot</option>
            </select>
          </div>
          <div className="form-group">
            <label>Search</label>
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Name, owner..."
            />
          </div>
          <div className="form-group">
            <label>Risk Min</label>
            <input
              type="number"
              value={riskMin}
              onChange={(e) => setRiskMin(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="0"
              min="0"
              max="100"
              style={{ width: '80px' }}
            />
          </div>
          <div className="form-group">
            <label>Risk Max</label>
            <input
              type="number"
              value={riskMax}
              onChange={(e) => setRiskMax(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="100"
              min="0"
              max="100"
              style={{ width: '80px' }}
            />
          </div>
          <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
            <button className="btn btn-primary btn-sm" onClick={handleFilterApply}>Filter</button>
          </div>
        </div>

        {error && <div className="error-msg">{error}</div>}

        {loading ? (
          <div className="loading">Loading identities...</div>
        ) : (
          <>
            <table>
              <thead>
                <tr>
                  <th>Display Name</th>
                  <th>Type</th>
                  <th>Enclave</th>
                  <th>Owner</th>
                  <th>Linked System</th>
                  <th>Risk Score</th>
                  <th>Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {identities.length === 0 ? (
                  <tr><td colSpan={7} style={{ textAlign: 'center', color: '#999' }}>No identities found.</td></tr>
                ) : (
                  identities.map((ident) => {
                    const nd = ident.normalized_data as Record<string, unknown> | undefined
                    return (
                      <tr
                        key={ident.id}
                        className="clickable"
                        onClick={() => navigate(`/identities/${ident.id}`)}
                      >
                        <td><strong>{ident.display_name || (nd?.display_name as string) || '--'}</strong></td>
                        <td>{ident.type || ident.identity_type || '--'}</td>
                        <td>{ident.enclave_name || ident.enclave_id || '--'}</td>
                        <td>{ident.owner || (nd?.owner as string) || '--'}</td>
                        <td>{ident.linked_system || (nd?.linked_system as string) || '--'}</td>
                        <td>
                          <span className={riskClass(ident.risk_score)}>
                            {ident.risk_score != null ? ident.risk_score : '--'}
                          </span>
                        </td>
                        <td>{ident.last_seen ? new Date(ident.last_seen).toLocaleDateString() : '--'}</td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>

            <div className="pagination">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={!hasPrev}
              >
                Previous
              </button>
              <span>Page {page}</span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={!hasNext}
              >
                Next
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
