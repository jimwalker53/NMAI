import React, { useState, useEffect, useCallback, useRef, ChangeEvent } from 'react'
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Alert,
  Box,
  Breadcrumbs,
  Button,
  ButtonGroup,
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
  LinearProgress,
  Link,
  Paper,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
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

// ── Config form schema ───────────────────────────────────────────────

const configSchema = z.object({
  config: z.string().refine(
    (v) => {
      try {
        JSON.parse(v)
        return true
      } catch {
        return false
      }
    },
    'Config must be valid JSON',
  ),
  cron_expression: z.string().optional(),
})

type ConfigFormValues = z.infer<typeof configSchema>

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

// ── Component ────────────────────────────────────────────────────────

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

  // Config form
  const {
    register,
    handleSubmit,
    reset: resetConfig,
    watch,
    formState: { errors: configErrors },
  } = useForm<ConfigFormValues>({
    resolver: zodResolver(configSchema),
    defaultValues: { config: '{}', cron_expression: '' },
  })

  const cronValue = watch('cron_expression')

  // Sync form when connector data loads
  useEffect(() => {
    if (connector) {
      resetConfig({
        config: JSON.stringify(connector.config || {}, null, 2),
        cron_expression: connector.cron_expression || '',
      })
    }
  }, [connector, resetConfig])

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

  // Handlers
  const onSaveConfig = async (values: ConfigFormValues) => {
    try {
      await updateMut.mutateAsync({
        id: id!,
        data: {
          config: JSON.parse(values.config),
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
    return (
      <Alert severity="error">Connector not found.</Alert>
    )
  }

  const isFileType = connector.connector_type === 'adcs_file' || connector.connector_type === 'csv_file'

  return (
    <>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/connectors" underline="hover" color="inherit">
          Connectors
        </Link>
        <Typography color="text.primary">{connector.name}</Typography>
      </Breadcrumbs>

      {/* Header info */}
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Typography variant="body2" color="text.secondary">
          Type: <strong>{connector.connector_type}</strong>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Enclave: <strong>{connector.enclave_name || connector.enclave_id}</strong>
        </Typography>
        <Chip
          label={connector.enabled ? 'Enabled' : 'Disabled'}
          color={connector.enabled ? 'success' : 'default'}
          variant={connector.enabled ? 'filled' : 'outlined'}
        />
      </Stack>

      {/* Actions */}
      <Card sx={{ mb: 2 }}>
        <CardHeader title="Actions" />
        <CardContent>
          <ButtonGroup variant="outlined" sx={{ flexWrap: 'wrap' }}>
            <Button onClick={handleTest} disabled={testMut.isPending} color="primary">
              {testMut.isPending ? 'Testing...' : 'Test Connection'}
            </Button>
            <Button onClick={handleRun} disabled={runMut.isPending} color="success">
              {runMut.isPending ? 'Starting...' : 'Run Now'}
            </Button>
            <Button onClick={handleToggleEnabled} color="warning">
              {connector.enabled ? 'Disable' : 'Enable'}
            </Button>
            <Button onClick={() => setDeleteDialogOpen(true)} color="error">
              Delete
            </Button>
          </ButtonGroup>

          {testResult && (
            <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mt: 2 }}>
              {testResult.success
                ? `Connection test passed. ${testResult.message || ''}`
                : `Connection test failed: ${testResult.error || 'Unknown error'}`}
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Configuration */}
      <Card sx={{ mb: 2 }}>
        <CardHeader title="Configuration" />
        <CardContent>
          <Box component="form" onSubmit={handleSubmit(onSaveConfig)} noValidate>
            <TextField
              label="Config (JSON)"
              multiline
              minRows={6}
              {...register('config')}
              error={!!configErrors.config}
              helperText={configErrors.config?.message}
              sx={{ mb: 2, '& textarea': { fontFamily: 'monospace', fontSize: '0.85rem' } }}
            />
            <TextField
              label="Cron Expression"
              {...register('cron_expression')}
              placeholder="e.g. 0 2 * * *"
              helperText={`Schedule: ${describeCron(cronValue || '')}`}
              sx={{ mb: 2 }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={updateMut.isPending}
            >
              {updateMut.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </Box>
        </CardContent>
      </Card>

      {/* File Upload (for adcs_file / csv_file types) */}
      {isFileType && (
        <Card sx={{ mb: 2 }}>
          <CardHeader title="File Upload" />
          <CardContent>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload a CSV file to ingest identities for this connector.
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap" useFlexGap>
              <Button variant="outlined" component="label">
                Choose File
                <input
                  type="file"
                  hidden
                  accept=".csv,.tsv,.txt"
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
      <Card sx={{ mb: 2 }}>
        <CardHeader
          title="Job History"
          action={
            <Button
              variant="outlined"
              startIcon={<RefreshIcon />}
              onClick={() => refetchJobs()}
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
            Delete this connector? This cannot be undone.
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
