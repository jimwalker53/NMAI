import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios'

// ── Shared interfaces for API responses ──────────────────────────────

export interface LoginResponse {
  access_token: string
  token_type?: string
}

export interface Enclave {
  id: string
  name: string
  description?: string
  created_at?: string
}

export interface User {
  id: string
  username: string
  email?: string
  role_assignments?: RoleAssignment[]
}

export interface RoleAssignment {
  id: string
  role_name: string
  enclave_id?: string
  enclave_name?: string
}

export interface Connector {
  id: string
  name: string
  connector_type: string
  enclave_id?: string
  enclave_name?: string
  config?: Record<string, unknown>
  cron_expression?: string
  enabled: boolean
  last_run_at?: string
}

export interface ConnectorType {
  id?: string
  name?: string
  label?: string
}

export interface ConnectorJob {
  id?: string
  status: string
  started_at?: string
  finished_at?: string
  records_found?: number
  records_ingested?: number
  error?: string
}

export interface Identity {
  id: string
  display_name?: string
  type?: string
  identity_type?: string
  enclave_id?: string
  enclave_name?: string
  owner?: string
  linked_system?: string
  risk_score?: number
  last_seen?: string
  not_after?: string
  sans?: string[]
  finding_ids?: FindingRef[]
  risk_factors?: RiskFactor[] | Record<string, unknown>
  risk_breakdown?: RiskFactor[] | Record<string, unknown>
  normalized_data?: Record<string, unknown>
}

export interface FindingRef {
  id?: string
  finding_id?: string
  timestamp?: string
  created_at?: string
}

export interface RiskFactor {
  factor?: string
  name?: string
  score?: number
  weight?: number
}

export interface TestResult {
  success: boolean
  message?: string
  error?: string
}

export interface PaginatedResponse<T> {
  items?: T[]
  total?: number
}

export interface UploadResult {
  records_ingested?: number
}

// ── Axios client ─────────────────────────────────────────────────────

const client = axios.create({
  baseURL: '',
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach Bearer token ────────────────────────
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('nmia_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ── Response interceptor: redirect on 401 ───────────────────────────
client.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('nmia_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  },
)

// ── Auth ─────────────────────────────────────────────────────────────
export function login(username: string, password: string): Promise<AxiosResponse<LoginResponse>> {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  return client.post('/api/v1/auth/login', params, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

// ── Enclaves ─────────────────────────────────────────────────────────
export function getEnclaves(): Promise<AxiosResponse<Enclave[] | PaginatedResponse<Enclave>>> {
  return client.get('/api/v1/enclaves')
}
export function createEnclave(data: Partial<Enclave>): Promise<AxiosResponse<Enclave>> {
  return client.post('/api/v1/enclaves', data)
}
export function updateEnclave(id: string, data: Partial<Enclave>): Promise<AxiosResponse<Enclave>> {
  return client.put(`/api/v1/enclaves/${id}`, data)
}
export function deleteEnclave(id: string): Promise<AxiosResponse<void>> {
  return client.delete(`/api/v1/enclaves/${id}`)
}

// ── Users ────────────────────────────────────────────────────────────
export function getUsers(): Promise<AxiosResponse<User[] | PaginatedResponse<User>>> {
  return client.get('/api/v1/users')
}
export function createUser(data: { username: string; password: string; email?: string }): Promise<AxiosResponse<User>> {
  return client.post('/api/v1/users', data)
}
export function updateUser(id: string, data: Partial<User>): Promise<AxiosResponse<User>> {
  return client.put(`/api/v1/users/${id}`, data)
}
export function deleteUser(id: string): Promise<AxiosResponse<void>> {
  return client.delete(`/api/v1/users/${id}`)
}
export function assignRole(userId: string, data: { role_name: string; enclave_id?: string }): Promise<AxiosResponse<RoleAssignment>> {
  return client.post(`/api/v1/users/${userId}/roles`, data)
}
export function removeRole(userId: string, roleEnclaveId: string): Promise<AxiosResponse<void>> {
  return client.delete(`/api/v1/users/${userId}/roles/${roleEnclaveId}`)
}

// ── Connectors ───────────────────────────────────────────────────────
export function getConnector(id: string): Promise<AxiosResponse<Connector>> {
  return client.get(`/api/v1/connectors/${id}`)
}
export function getConnectorTypes(): Promise<AxiosResponse<(string | ConnectorType)[] | { types: (string | ConnectorType)[] }>> {
  return client.get('/api/v1/connectors/types')
}
export function getConnectors(): Promise<AxiosResponse<Connector[] | PaginatedResponse<Connector>>> {
  return client.get('/api/v1/connectors')
}
export function createConnector(data: {
  name: string
  connector_type: string
  enclave_id: string
  config: Record<string, unknown>
  cron_expression?: string | null
}): Promise<AxiosResponse<Connector>> {
  return client.post('/api/v1/connectors', data)
}
export function updateConnector(id: string, data: Partial<Connector>): Promise<AxiosResponse<Connector>> {
  return client.put(`/api/v1/connectors/${id}`, data)
}
export function deleteConnector(id: string): Promise<AxiosResponse<void>> {
  return client.delete(`/api/v1/connectors/${id}`)
}
export function testConnector(id: string): Promise<AxiosResponse<TestResult>> {
  return client.post(`/api/v1/connectors/${id}/test`)
}
export function runConnector(id: string): Promise<AxiosResponse<void>> {
  return client.post(`/api/v1/connectors/${id}/run`)
}
export function getConnectorJobs(id: string): Promise<AxiosResponse<ConnectorJob[] | PaginatedResponse<ConnectorJob>>> {
  return client.get(`/api/v1/connectors/${id}/jobs`)
}

// ── Ingest (CSV upload) ──────────────────────────────────────────────
export function uploadCSV(connectorId: string, file: File): Promise<AxiosResponse<UploadResult>> {
  const formData = new FormData()
  formData.append('file', file)
  return client.post(`/api/v1/ingest/adcs/${connectorId}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ── Identities ───────────────────────────────────────────────────────
export interface IdentityQueryParams {
  limit?: number
  offset?: number
  enclave_id?: string
  type?: string
  search?: string
  risk_score_min?: number
  risk_score_max?: number
}

export function getIdentities(params: IdentityQueryParams = {}): Promise<AxiosResponse<Identity[] | PaginatedResponse<Identity>>> {
  return client.get('/api/v1/identities', { params })
}
export function getIdentity(id: string): Promise<AxiosResponse<Identity>> {
  return client.get(`/api/v1/identities/${id}`)
}
export function updateIdentity(id: string, data: Partial<Identity>): Promise<AxiosResponse<Identity>> {
  return client.put(`/api/v1/identities/${id}`, data)
}

// ── Reports ──────────────────────────────────────────────────────────
export function getExpiringReport(days: number = 90): Promise<AxiosResponse<Identity[] | PaginatedResponse<Identity>>> {
  return client.get('/api/v1/reports/expiring', { params: { days } })
}
export function getOrphanedReport(): Promise<AxiosResponse<Identity[] | PaginatedResponse<Identity>>> {
  return client.get('/api/v1/reports/orphaned')
}

export default client
