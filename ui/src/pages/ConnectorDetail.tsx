import React, { useState, useEffect, ChangeEvent } from 'react'
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControlLabel,
  LinearProgress,
  Link,
  MenuItem,
  Snackbar,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import NetworkCheckIcon from '@mui/icons-material/NetworkCheck'
import RefreshIcon from '@mui/icons-material/Refresh'
import DeleteIcon from '@mui/icons-material/Delete'
import UploadFileIcon from '@mui/icons-material/UploadFile'
import {
  TestResult,
  useConnector,
  useConnectorJobs,
  useUpdateConnector,
  useDeleteConnector,
  useTestConnector,
  useRunConnector,
  useUploadCSV,
} from '../api/client'

// ── Cron helper ──────────────────────────────────────────────────────

function describeCron(expr: string): string {
  if (!expr) return 'Not scheduled'
  const parts = expr.trim().split(/\s+/)
  if (parts.length !== 5) return 'Invalid cron expression (need 5 fields: min hour dom mon dow)'
  const [min, hr, dom, mon, dow] = parts
  if (min === '*' && hr === '*' && dom === '*' && mon === '*' && dow === '*') return 'Every minute'
  if (min.startsWith('*/')) return `Every ${min.slice(2)} minutes`
  if (hr.startsWith('*/')) return `Every ${hr.slice(2)} hours`
  if (min === '0' && hr !== '*' && dom === '*' && mon === '*' && dow === '*') {
    return `Daily at ${hr.padStart(2, '0')}:00`
  }
  if (min !== '*' && hr !== '*' && dom === '*' && mon === '*' && dow !== '*') {
    const days: Record<string, string> = { 0: 'Sun', 1: 'Mon', 2: 'Tue', 3: 'Wed', 4: 'Thu', 5: 'Fri', 6: 'Sat' }
    return `${days[dow] || dow} at ${hr.padStart(2, '0')}:${min.padStart(2, '0')}`
  }
  return `Cron: ${expr}`
}

function isValidCron(expr: string): boolean {
  if (!expr) return true
  const parts = expr.trim().split(/\s+/)
  return parts.length === 5
}

// ── Type-specific config schemas ────────────────────────────────────

interface ADLDAPConfig {
  server: string
  port: number
  use_ssl: boolean
  bind_dn: string
  bind_password: string
  search_base: string
  search_filter: string
}

interface ADCSFileConfig {
  delimiter: string
  encoding: string
}

interface ADCSRemoteConfig {
  ca_host: string
  ca_name: string
  use_ssl: boolean
  username: string
  password: string
}

const AD_LDAP_DEFAULTS: ADLDAPConfig = {
  server: '',
  port: 389,
  use_ssl: false,
  bind_dn: '',
  bind_password: '',
  search_base: '',
  search_filter: '(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*))',
}

const ADCS_FILE_DEFAULTS: ADCSFileConfig = {
  delimiter: ',',
  encoding: 'utf-8',
}

const ADCS_REMOTE_DEFAULTS: ADCSRemoteConfig = {
  ca_host: '',
  ca_name: '',
  use_ssl: true,
  username: '',
  password: '',
}

// ── Main form schema ────────────────────────────────────────────────

const detailSchema = z.object({
  cron_expression: z.string().optional(),
})

type DetailFormValues = z.infer<typeof detailSchema>

// ── Job status chip color helper ────────────────────────────────────

function jobChipColor(status: string): 'success' | 'error' | 'info' | 'warning' | 'default' {
  switch (status) {
    case 'completed':
    case 'success':
      return 'success'
    case 'failed':
    case 'error':
      return 'error'
    case 'running':
      return 'info'
    case 'queued':
    case 'pending':
      return 'warning'
    default:
      return 'default'
  }
}

// ── AD LDAP Config Form ─────────────────────────────────────────────

function ADLDAPConfigForm({
  config,
  onChange,
}: {
  config: ADLDAPConfig
  onChange: (c: ADLDAPConfig) => void
}) {
  const update = (field: keyof ADLDAPConfig, value: string | number | boolean) => {
    onChange({ ...config, [field]: value })
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2}>
        <TextField
          label="LDAP Server"
          value={config.server}
          onChange={(e) => update('server', e.target.value)}
          placeholder="ldap://dc01.corp.local"
          sx={{ flex: 2 }}
        />
        <TextField
          label="Port"
          type="number"
          value={config.port}
          onChange={(e) => update('port', Number(e.target.value))}
          sx={{ width: 100 }}
        />
        <FormControlLabel
          control={
            <Switch
              checked={config.use_ssl}
              onChange={(e) => update('use_ssl', e.target.checked)}
            />
          }
          label="SSL"
          sx={{ ml: 0 }}
        />
      </Stack>
      <TextField
        label="Bind DN"
        value={config.bind_dn}
        onChange={(e) => update('bind_dn', e.target.value)}
        placeholder="CN=svc-nmia,OU=ServiceAccounts,DC=corp,DC=local"
      />
      <TextField
        label="Bind Password"
        type="password"
        value={config.bind_password}
        onChange={(e) => update('bind_password', e.target.value)}
      />
      <TextField
        label="Search Base"
        value={config.search_base}
        onChange={(e) => update('search_base', e.target.value)}
        placeholder="DC=corp,DC=local"
      />
      <TextField
        label="Search Filter"
        value={config.search_filter}
        onChange={(e) => update('search_filter', e.target.value)}
        placeholder="(&(objectCategory=person)(objectClass=user)(servicePrincipalName=*))"
        multiline
        minRows={2}
        sx={{ '& textarea': { fontFamily: 'monospace', fontSize: '0.85rem' } }}
      />
    </Stack>
  )
}

// ── ADCS File Config Form ───────────────────────────────────────────

function ADCSFileConfigForm({
  config,
  onChange,
}: {
  config: ADCSFileConfig
  onChange: (c: ADCSFileConfig) => void
}) {
  return (
    <Stack direction="row" spacing={2}>
      <TextField
        label="CSV Delimiter"
        value={config.delimiter}
        onChange={(e) => onChange({ ...config, delimiter: e.target.value })}
        sx={{ width: 120 }}
      />
      <TextField
        label="Encoding"
        select
        value={config.encoding}
        onChange={(e) => onChange({ ...config, encoding: e.target.value })}
        sx={{ width: 160 }}
      >
        <MenuItem value="utf-8">UTF-8</MenuItem>
        <MenuItem value="utf-16">UTF-16</MenuItem>
        <MenuItem value="latin-1">Latin-1</MenuItem>
      </TextField>
    </Stack>
  )
}

// ── ADCS Remote Config Form ─────────────────────────────────────────

function ADCSRemoteConfigForm({
  config,
  onChange,
}: {
  config: ADCSRemoteConfig
  onChange: (c: ADCSRemoteConfig) => void
}) {
  const update = (field: keyof ADCSRemoteConfig, value: string | boolean) => {
    onChange({ ...config, [field]: value })
  }

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={2}>
        <TextField
          label="CA Host"
          value={config.ca_host}
          onChange={(e) => update('ca_host', e.target.value)}
          placeholder="ca01.corp.local"
          sx={{ flex: 1 }}
        />
        <TextField
          label="CA Name"
          value={config.ca_name}
          onChange={(e) => update('ca_name', e.target.value)}
          placeholder="Corp-Issuing-CA"
          sx={{ flex: 1 }}
        />
        <FormControlLabel
          control={
            <Switch
              checked={config.use_ssl}
              onChange={(e) => update('use_ssl', e.target.checked)}
            />
          }
          label="SSL"
        />
      </Stack>
      <TextField
        label="Username"
        value={config.username}
        onChange={(e) => update('username', e.target.value)}
        placeholder="DOMAIN\\svc-nmia"
      />
      <TextField
        label="Password"
        type="password"
        value={config.password}
        onChange={(e) => update('password', e.target.value)}
      />
    </Stack>
  )
}

// ── JSON Fallback Config Form ───────────────────────────────────────

function JSONConfigForm({
  value,
  onChange,
}: {
  value: string
  onChange: (v: string) => void
}) {
  const [error, setError] = useState('')

  const handleChange = (v: string) => {
    onChange(v)
    try {
      JSON.parse(v)
      setError('')
    } catch {
      setError('Invalid JSON')
    }
  }

  return (
    <TextField
      label="Config (JSON)"
      multiline
      minRows={6}
      value={value}
      onChange={(e) => handleChange(e.target.value)}
      error={!!error}
      helperText={error}
      sx={{ '& textarea': { fontFamily: 'monospace', fontSize: '0.85rem' } }}
    />
  )
}

// ── Main Component ──────────────────────────────────────────────────

export default function ConnectorDetail(): React.ReactElement {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  // Polling state
  const [polling, setPolling] = useState(false)

  // React Query hooks
  const { data: connector, isLoading, error: connError, refetch: refetchConnector } = useConnector(id!)
  const { data: jobs = [], refetch: refetchJobs } = useConnectorJobs(id!, polling ? 3000 : false)
  const updateMut = useUpdateConnector()
  const deleteMut = useDeleteConnector()
  const testMut = useTestConnector()
  const runMut = useRunConnector()
  const uploadMut = useUploadCSV()

  // Config state (type-specific)
  const [adLdapConfig, setAdLdapConfig] = useState<ADLDAPConfig>(AD_LDAP_DEFAULTS)
  const [adcsFileConfig, setAdcsFileConfig] = useState<ADCSFileConfig>(ADCS_FILE_DEFAULTS)
  const [adcsRemoteConfig, setAdcsRemoteConfig] = useState<ADCSRemoteConfig>(ADCS_REMOTE_DEFAULTS)
  const [jsonConfig, setJsonConfig] = useState('{}')

  // Local state
  const [testResult, setTestResult] = useState<TestResult | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })

  const showSnack = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity })
  }

  // Cron form
  const {
    register,
    handleSubmit,
    reset: resetForm,
    watch,
  } = useForm<DetailFormValues>({
    resolver: zodResolver(detailSchema),
    defaultValues: { cron_expression: '' },
  })

  const cronValue = watch('cron_expression')

  // Determine connector type category
  const connectorType = connector?.connector_type || ''
  const isADLDAP = connectorType === 'ad_ldap'
  const isADCSFile = connectorType === 'adcs_file'
  const isADCSRemote = connectorType === 'adcs_remote'
  const isFileType = isADCSFile || connectorType === 'csv_file'

  // Sync form when connector data loads
  useEffect(() => {
    if (connector) {
      resetForm({ cron_expression: connector.cron_expression || '' })

      const cfg = connector.config || {}

      if (isADLDAP) {
        setAdLdapConfig({
          server: (cfg.server as string) || '',
          port: (cfg.port as number) || 389,
          use_ssl: (cfg.use_ssl as boolean) || false,
          bind_dn: (cfg.bind_dn as string) || '',
          bind_password: (cfg.bind_password as string) || '',
          search_base: (cfg.search_base as string) || '',
          search_filter: (cfg.search_filter as string) || AD_LDAP_DEFAULTS.search_filter,
        })
      } else if (isADCSFile) {
        setAdcsFileConfig({
          delimiter: (cfg.delimiter as string) || ',',
          encoding: (cfg.encoding as string) || 'utf-8',
        })
      } else if (isADCSRemote) {
        setAdcsRemoteConfig({
          ca_host: (cfg.ca_host as string) || '',
          ca_name: (cfg.ca_name as string) || '',
          use_ssl: (cfg.use_ssl as boolean) ?? true,
          username: (cfg.username as string) || '',
          password: (cfg.password as string) || '',
        })
      } else {
        setJsonConfig(JSON.stringify(cfg, null, 2))
      }
    }
  }, [connector, resetForm, isADLDAP, isADCSFile, isADCSRemote])

  // Auto-start/stop polling when jobs have running status
  useEffect(() => {
    const hasRunning = jobs.some((j) => j.status === 'running' || j.status === 'queued')
    if (hasRunning && !polling) {
      setPolling(true)
    } else if (!hasRunning && polling) {
      setPolling(false)
      refetchConnector()
    }
  }, [jobs, polling, refetchConnector])

  // Build config object from current state
  const buildConfig = (): Record<string, unknown> => {
    if (isADLDAP) return { ...adLdapConfig }
    if (isADCSFile) return { ...adcsFileConfig }
    if (isADCSRemote) return { ...adcsRemoteConfig }
    try {
      return JSON.parse(jsonConfig)
    } catch {
      return {}
    }
  }

  // Handlers
  const onSaveConfig = async (values: DetailFormValues) => {
    try {
      await updateMut.mutateAsync({
        id: id!,
        data: {
          config: buildConfig(),
          cron_expression: values.cron_expression || undefined,
        },
      })
      showSnack('Connector updated.', 'success')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to update connector.'
      showSnack(msg, 'error')
    }
  }

  const handleTest = async () => {
    setTestResult(null)
    try {
      const result = await testMut.mutateAsync(id!)
      setTestResult(result)
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Test failed.'
      setTestResult({ success: false, error: detail })
    }
  }

  const handleRun = async () => {
    try {
      await runMut.mutateAsync(id!)
      showSnack('Connector run started.', 'success')
      setPolling(true)
      refetchJobs()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to start connector run.'
      showSnack(msg, 'error')
    }
  }

  const handleToggleEnabled = async () => {
    if (!connector) return
    try {
      await updateMut.mutateAsync({ id: id!, data: { enabled: !connector.enabled } })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to toggle connector.'
      showSnack(msg, 'error')
    }
  }

  const handleDelete = async () => {
    try {
      await deleteMut.mutateAsync(id!)
      navigate('/connectors', { replace: true })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to delete connector.'
      showSnack(msg, 'error')
    }
    setDeleteDialogOpen(false)
  }

  const handleUpload = async () => {
    if (!selectedFile) return
    try {
      const res = await uploadMut.mutateAsync({ connectorId: id!, file: selectedFile })
      showSnack(`Upload complete. ${res.data.records_ingested ?? 'Records'} ingested.`, 'success')
      setSelectedFile(null)
      refetchJobs()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed.'
      showSnack(msg, 'error')
    }
  }

  // Loading / error states
  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (connError || !connector) {
    return <Alert severity="error">Connector not found.</Alert>
  }

  const connectorTypeLabel = connectorType
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/connectors" underline="hover" color="inherit">
          Connectors
        </Link>
        <Typography color="text.primary">{connector.name}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Typography variant="h5">{connector.name}</Typography>
        <Chip label={connectorTypeLabel} variant="outlined" />
        <Chip
          label={connector.enabled ? 'Enabled' : 'Disabled'}
          color={connector.enabled ? 'success' : 'default'}
          variant={connector.enabled ? 'filled' : 'outlined'}
        />
        <Typography variant="body2" color="text.secondary">
          Enclave: {connector.enclave_name || connector.enclave_id}
        </Typography>
      </Stack>

      {/* Actions */}
      <Stack direction="row" spacing={1} sx={{ mb: 3 }} flexWrap="wrap" useFlexGap>
        <Button
          variant="outlined"
          startIcon={<NetworkCheckIcon />}
          onClick={handleTest}
          disabled={testMut.isPending}
        >
          {testMut.isPending ? 'Testing...' : 'Test'}
        </Button>
        <Button
          variant="contained"
          startIcon={<PlayArrowIcon />}
          onClick={handleRun}
          disabled={runMut.isPending}
          color="success"
        >
          {runMut.isPending ? 'Starting...' : 'Run Now'}
        </Button>
        <Button variant="outlined" color="warning" onClick={handleToggleEnabled}>
          {connector.enabled ? 'Disable' : 'Enable'}
        </Button>
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={() => setDeleteDialogOpen(true)}
        >
          Delete
        </Button>
      </Stack>

      {testResult && (
        <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mb: 2 }}>
          {testResult.success
            ? `Connection test passed. ${testResult.message || ''}`
            : `Connection test failed: ${testResult.error || 'Unknown error'}`}
        </Alert>
      )}

      {/* Configuration */}
      <Card sx={{ mb: 3 }}>
        <CardHeader title="Configuration" />
        <CardContent>
          <Box component="form" onSubmit={handleSubmit(onSaveConfig)} noValidate>
            {/* Type-specific config fields */}
            {isADLDAP && (
              <ADLDAPConfigForm config={adLdapConfig} onChange={setAdLdapConfig} />
            )}
            {isADCSFile && (
              <ADCSFileConfigForm config={adcsFileConfig} onChange={setAdcsFileConfig} />
            )}
            {isADCSRemote && (
              <ADCSRemoteConfigForm config={adcsRemoteConfig} onChange={setAdcsRemoteConfig} />
            )}
            {!isADLDAP && !isADCSFile && !isADCSRemote && (
              <JSONConfigForm value={jsonConfig} onChange={setJsonConfig} />
            )}

            <Divider sx={{ my: 2 }} />

            {/* Cron editor */}
            <TextField
              label="Cron Schedule"
              {...register('cron_expression')}
              placeholder="e.g. 0 2 * * *"
              helperText={
                cronValue && !isValidCron(cronValue)
                  ? 'Invalid: use 5 fields — min hour dom mon dow'
                  : describeCron(cronValue || '')
              }
              error={!!cronValue && !isValidCron(cronValue)}
              sx={{ mb: 2 }}
            />

            <Button
              type="submit"
              variant="contained"
              disabled={updateMut.isPending}
            >
              {updateMut.isPending ? 'Saving...' : 'Save Configuration'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* File Upload (for ADCS file / CSV types) */}
      {isFileType && (
        <Card sx={{ mb: 3 }}>
          <CardHeader title="File Upload" />
          <CardContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload a CSV file to ingest certificate data for this connector.
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
              <Button variant="outlined" component="label" startIcon={<UploadFileIcon />}>
                Choose File
                <input
                  type="file"
                  hidden
                  accept=".csv,.tsv,.txt,.json"
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setSelectedFile(e.target.files?.[0] || null)}
                />
              </Button>
              {selectedFile && (
                <Typography variant="body2">{selectedFile.name}</Typography>
              )}
              <Button
                variant="contained"
                onClick={handleUpload}
                disabled={!selectedFile || uploadMut.isPending}
              >
                {uploadMut.isPending ? 'Uploading...' : 'Upload'}
              </Button>
            </Stack>
            {uploadMut.isPending && <LinearProgress sx={{ mt: 1 }} />}
          </CardContent>
        </Card>
      )}

      {/* Job History */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Job History"
          action={
            <Button
              variant="text"
              startIcon={<RefreshIcon />}
              onClick={() => refetchJobs()}
              size="small"
            >
              Refresh
            </Button>
          }
        />
        <CardContent>
          {jobs.length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              No jobs recorded yet.
            </Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Status</TableCell>
                  <TableCell>Started</TableCell>
                  <TableCell>Finished</TableCell>
                  <TableCell>Found</TableCell>
                  <TableCell>Ingested</TableCell>
                  <TableCell>Error</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {jobs.map((j, idx) => (
                  <TableRow key={j.id || idx} hover>
                    <TableCell>
                      <Chip label={j.status} color={jobChipColor(j.status)} />
                    </TableCell>
                    <TableCell>
                      {j.started_at ? new Date(j.started_at).toLocaleString() : '--'}
                    </TableCell>
                    <TableCell>
                      {j.finished_at ? new Date(j.finished_at).toLocaleString() : '--'}
                    </TableCell>
                    <TableCell>{j.records_found ?? '--'}</TableCell>
                    <TableCell>{j.records_ingested ?? '--'}</TableCell>
                    <TableCell sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {j.error || '--'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>Delete Connector</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete &ldquo;{connector.name}&rdquo;? This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert
          onClose={() => setSnackbar((s) => ({ ...s, open: false }))}
          severity={snackbar.severity}
          variant="filled"
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </>
  )
}
