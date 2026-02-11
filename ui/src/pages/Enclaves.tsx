import React, { useState } from 'react'
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
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  Snackbar,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import AddIcon from '@mui/icons-material/Add'
import { useAuth } from '../auth/AuthContext'
import {
  Enclave,
  useEnclaves,
  useCreateEnclave,
  useUpdateEnclave,
  useDeleteEnclave,
} from '../api/client'

const enclaveSchema = z.object({
  name: z.string().min(1, 'Name is required'),
  description: z.string().optional(),
})

type EnclaveFormValues = z.infer<typeof enclaveSchema>

export default function Enclaves(): React.ReactElement {
  const { isAdmin } = useAuth()
  const { data: enclaves = [], isLoading, error: queryError } = useEnclaves()
  const createMutation = useCreateEnclave()
  const updateMutation = useUpdateEnclave()
  const deleteMutation = useDeleteEnclave()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
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
  } = useForm<EnclaveFormValues>({
    resolver: zodResolver(enclaveSchema),
    defaultValues: { name: '', description: '' },
  })

  const openCreate = () => {
    reset({ name: '', description: '' })
    setEditingId(null)
    setDialogOpen(true)
  }

  const openEdit = (enc: Enclave) => {
    reset({ name: enc.name, description: enc.description || '' })
    setEditingId(enc.id)
    setDialogOpen(true)
  }

  const closeDialog = () => {
    setDialogOpen(false)
    setEditingId(null)
  }

  const onSubmit = async (values: EnclaveFormValues) => {
    try {
      if (editingId) {
        await updateMutation.mutateAsync({ id: editingId, data: values })
        setSnackbar({ open: true, message: 'Enclave updated.', severity: 'success' })
      } else {
        await createMutation.mutateAsync(values)
        setSnackbar({ open: true, message: 'Enclave created.', severity: 'success' })
      }
      closeDialog()
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to save enclave.'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this enclave? This cannot be undone.')) return
    try {
      await deleteMutation.mutateAsync(id)
      setSnackbar({ open: true, message: 'Enclave deleted.', severity: 'success' })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to delete enclave.'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    }
  }

  return (
    <>
      <Card>
        <CardHeader
          title="Enclaves"
          action={
            isAdmin ? (
              <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
                Add Enclave
              </Button>
            ) : undefined
          }
        />
        <CardContent>
          {queryError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to load enclaves.
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
                  <TableCell>Description</TableCell>
                  <TableCell>Created</TableCell>
                  {isAdmin && <TableCell>Actions</TableCell>}
                </TableRow>
              </TableHead>
              <TableBody>
                {enclaves.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={isAdmin ? 4 : 3} align="center">
                      <Typography color="text.secondary" variant="body2">
                        No enclaves found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  enclaves.map((enc) => (
                    <TableRow key={enc.id} hover>
                      <TableCell>
                        <Typography fontWeight={600}>{enc.name}</Typography>
                      </TableCell>
                      <TableCell>{enc.description || '--'}</TableCell>
                      <TableCell>
                        {enc.created_at ? new Date(enc.created_at).toLocaleDateString() : '--'}
                      </TableCell>
                      {isAdmin && (
                        <TableCell>
                          <IconButton size="small" onClick={() => openEdit(enc)} color="primary">
                            <EditIcon fontSize="small" />
                          </IconButton>
                          <IconButton size="small" onClick={() => handleDelete(enc.id)} color="error">
                            <DeleteIcon fontSize="small" />
                          </IconButton>
                        </TableCell>
                      )}
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onClose={closeDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingId ? 'Edit Enclave' : 'New Enclave'}</DialogTitle>
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
              label="Description"
              {...register('description')}
              error={!!errors.description}
              helperText={errors.description?.message}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closeDialog}>Cancel</Button>
            <Button
              type="submit"
              variant="contained"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {editingId ? 'Update' : 'Create'}
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
