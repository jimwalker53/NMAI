import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import {
  ConnectorType,
  useConnectors,
  useConnectorTypes,
  useEnclaves,
  useCreateConnector,
} from '../api/client'

const connectorSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  connector_type_code: z.string().min(1, 'Type is required'),
  enclave_id: z.string().min(1, 'Enclave is required'),
  config: z.string().refine(
    (v) => {
      try {
        JSON.parse(v)
        return true
      } catch {
        return false
      }
    },
    'Invalid JSON',
  ),
  cron_expression: z.string().optional(),
})

type ConnectorFormValues = z.infer<typeof connectorSchema>

export default function Connectors(): React.ReactElement {
  const navigate = useNavigate()
  const { data: connectors = [], isLoading, error: queryError } = useConnectors()
  const { data: connectorTypes = [] } = useConnectorTypes()
  const { data: enclaves = [] } = useEnclaves()
  const createMut = useCreateConnector()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConnectorFormValues>({
    resolver: zodResolver(connectorSchema),
    defaultValues: {
      name: '',
      connector_type_code: '',
      enclave_id: '',
      config: '{}',
      cron_expression: '',
    },
  })

  const openCreate = () => {
    reset({ name: '', connector_type_code: '', enclave_id: '', config: '{}', cron_expression: '' })
    setDialogOpen(true)
  }

  const onSubmit = async (values: ConnectorFormValues) => {
    try {
      await createMut.mutateAsync({
        name: values.name,
        connector_type: values.connector_type_code,
        enclave_id: values.enclave_id,
        config: JSON.parse(values.config),
        cron_expression: values.cron_expression || null,
      })
      setSnackbar({ open: true, message: 'Connector created.', severity: 'success' })
      setDialogOpen(false)
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to create connector.'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    }
  }

  return (
    <>
      <Card>
        <CardHeader
          title="Connectors"
          action={
            <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
              Add Connector
            </Button>
          }
        />
        <CardContent>
          {queryError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to load connectors.
            </Alert>
          )}

          {isLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Enclave</TableCell>
                  <TableCell>Cron</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Run</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {connectors.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} align="center">
                      <Typography color="text.secondary" variant="body2">
                        No connectors configured.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  connectors.map((c) => (
                    <TableRow
                      key={c.id}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => navigate(`/connectors/${c.id}`)}
                    >
                      <TableCell>
                        <Typography fontWeight={600}>{c.name}</Typography>
                      </TableCell>
                      <TableCell>{c.connector_type}</TableCell>
                      <TableCell>{c.enclave_name || c.enclave_id || '--'}</TableCell>
                      <TableCell>
                        <Typography variant="body2" fontFamily="monospace">
                          {c.cron_expression || '--'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={c.enabled ? 'Enabled' : 'Disabled'}
                          color={c.enabled ? 'success' : 'default'}
                          variant={c.enabled ? 'filled' : 'outlined'}
                        />
                      </TableCell>
                      <TableCell>
                        {c.last_run_at ? new Date(c.last_run_at).toLocaleString() : '--'}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>New Connector</DialogTitle>
        <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
          <DialogContent>
            <TextField
              label="Name"
              {...register('name')}
              error={!!errors.name}
              helperText={errors.name?.message}
              autoFocus
              sx={{ mb: 2 }}
            />
            <TextField
              label="Type"
              select
              {...register('connector_type_code')}
              error={!!errors.connector_type_code}
              helperText={errors.connector_type_code?.message}
              sx={{ mb: 2 }}
              defaultValue=""
            >
              <MenuItem value="">Select type...</MenuItem>
              {connectorTypes.map((t) => {
                const val = typeof t === 'string' ? t : t.name || t.id || ''
                const label = typeof t === 'string' ? t : t.label || t.name || t.id || ''
                return (
                  <MenuItem key={val} value={val}>
                    {label}
                  </MenuItem>
                )
              })}
            </TextField>
            <TextField
              label="Enclave"
              select
              {...register('enclave_id')}
              error={!!errors.enclave_id}
              helperText={errors.enclave_id?.message}
              sx={{ mb: 2 }}
              defaultValue=""
            >
              <MenuItem value="">Select enclave...</MenuItem>
              {enclaves.map((enc) => (
                <MenuItem key={enc.id} value={enc.id}>
                  {enc.name}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Config (JSON)"
              multiline
              minRows={4}
              {...register('config')}
              error={!!errors.config}
              helperText={errors.config?.message}
              sx={{ mb: 2, '& textarea': { fontFamily: 'monospace', fontSize: '0.85rem' } }}
            />
            <TextField
              label="Cron Expression"
              {...register('cron_expression')}
              placeholder="e.g. 0 2 * * *"
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={createMut.isPending}>
              Create
            </Button>
          </DialogActions>
        </Box>
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
