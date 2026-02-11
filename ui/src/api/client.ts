import axios, { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

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

// ── Helper to normalize API list responses ──────────────────────────

function normalizeList<T>(data: T[] | PaginatedResponse<T>): T[] {
  return Array.isArray(data) ? data : (data.items ?? [])
}

function normalizeConnectorTypes(
  data: (string | ConnectorType)[] | { types: (string | ConnectorType)[] },
): (string | ConnectorType)[] {
  return Array.isArray(data) ? data : (data.types ?? [])
}

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

// ══════════════════════════════════════════════════════════════════════
// ── React Query Keys ────────────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════

export const queryKeys = {
  enclaves: ['enclaves'] as const,
  users: ['users'] as const,
  connectorTypes: ['connectorTypes'] as const,
  connectors: ['connectors'] as const,
  connector: (id: string) => ['connector', id] as const,
  connectorJobs: (id: string) => ['connectorJobs', id] as const,
  identities: (params: IdentityQueryParams) => ['identities', params] as const,
  identity: (id: string) => ['identity', id] as const,
  expiringReport: (days: number) => ['expiringReport', days] as const,
  orphanedReport: ['orphanedReport'] as const,
}

// ══════════════════════════════════════════════════════════════════════
// ── React Query Hooks – Enclaves ────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════

export function useEnclaves() {
  return useQuery({
    queryKey: queryKeys.enclaves,
    queryFn: () => getEnclaves().then((r) => normalizeList(r.data)),
  })
}

export function useCreateEnclave() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Partial<Enclave>) => createEnclave(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.enclaves }),
  })
}

export function useUpdateEnclave() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Enclave> }) => updateEnclave(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.enclaves }),
  })
}

export function useDeleteEnclave() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteEnclave(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.enclaves }),
  })
}

// ══════════════════════════════════════════════════════════════════════
// ── React Query Hooks – Users ───────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════

export function useUsers() {
  return useQuery({
    queryKey: queryKeys.users,
    queryFn: () => getUsers().then((r) => normalizeList(r.data)),
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { username: string; password: string; email?: string }) => createUser(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users }),
  })
}

export function useDeleteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users }),
  })
}

export function useAssignRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: { role_name: string; enclave_id?: string } }) =>
      assignRole(userId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users }),
  })
}

export function useRemoveRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, roleEnclaveId }: { userId: string; roleEnclaveId: string }) =>
      removeRole(userId, roleEnclaveId),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.users }),
  })
}

// ══════════════════════════════════════════════════════════════════════
// ── React Query Hooks – Connectors ──────────────────────────────────
// ══════════════════════════════════════════════════════════════════════

export function useConnectorTypes() {
  return useQuery({
    queryKey: queryKeys.connectorTypes,
    queryFn: () => getConnectorTypes().then((r) => normalizeConnectorTypes(r.data)),
  })
}

export function useConnectors() {
  return useQuery({
    queryKey: queryKeys.connectors,
    queryFn: () => getConnectors().then((r) => normalizeList(r.data)),
  })
}

export function useConnector(id: string) {
  return useQuery({
    queryKey: queryKeys.connector(id),
    queryFn: () => getConnector(id).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateConnector() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: {
      name: string
      connector_type: string
      enclave_id: string
      config: Record<string, unknown>
      cron_expression?: string | null
    }) => createConnector(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectors }),
  })
}

export function useUpdateConnector() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Connector> }) => updateConnector(id, data),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.connectors })
      qc.invalidateQueries({ queryKey: queryKeys.connector(vars.id) })
    },
  })
}

export function useDeleteConnector() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => deleteConnector(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.connectors }),
  })
}

export function useTestConnector() {
  return useMutation({
    mutationFn: (id: string) => testConnector(id).then((r) => r.data),
  })
}

export function useRunConnector() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => runConnector(id),
    onSuccess: (_res, id) => {
      qc.invalidateQueries({ queryKey: queryKeys.connectorJobs(id) })
    },
  })
}

export function useConnectorJobs(id: string, refetchInterval?: number | false) {
  return useQuery({
    queryKey: queryKeys.connectorJobs(id),
    queryFn: () => getConnectorJobs(id).then((r) => normalizeList(r.data)),
    enabled: !!id,
    refetchInterval: refetchInterval ?? false,
  })
}

// ── Ingest (CSV) ────────────────────────────────────────────────────

export function useUploadCSV() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ connectorId, file }: { connectorId: string; file: File }) => uploadCSV(connectorId, file),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.connectorJobs(vars.connectorId) })
    },
  })
}

// ══════════════════════════════════════════════════════════════════════
// ── React Query Hooks – Identities ──────────────────────────────────
// ══════════════════════════════════════════════════════════════════════

export function useIdentities(params: IdentityQueryParams) {
  return useQuery({
    queryKey: queryKeys.identities(params),
    queryFn: async () => {
      const res = await getIdentities(params)
      if (Array.isArray(res.data)) {
        return { items: res.data, total: res.data.length }
      }
      const paginated = res.data as PaginatedResponse<Identity>
      return { items: paginated.items ?? [], total: paginated.total ?? paginated.items?.length ?? 0 }
    },
  })
}

export function useIdentity(id: string) {
  return useQuery({
    queryKey: queryKeys.identity(id),
    queryFn: () => getIdentity(id).then((r) => r.data),
    enabled: !!id,
  })
}

export function useUpdateIdentity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<Identity> }) => updateIdentity(id, data),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: queryKeys.identity(vars.id) })
    },
  })
}

// ══════════════════════════════════════════════════════════════════════
// ── React Query Hooks – Reports ─────────────────────────────────────
// ══════════════════════════════════════════════════════════════════════

export function useExpiringReport(days: number) {
  return useQuery({
    queryKey: queryKeys.expiringReport(days),
    queryFn: () => getExpiringReport(days).then((r) => normalizeList(r.data)),
  })
}

export function useOrphanedReport() {
  return useQuery({
    queryKey: queryKeys.orphanedReport,
    queryFn: () => getOrphanedReport().then((r) => normalizeList(r.data)),
  })
}

export default client
