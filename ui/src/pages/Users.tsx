import React, { useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
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
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import {
  useUsers,
  useCreateUser,
  useDeleteUser,
  useAssignRole,
  useRemoveRole,
  useEnclaves,
} from '../api/client'

// ── Schemas ──────────────────────────────────────────────────────────

const createUserSchema = z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(6, 'Min 6 chars'),
  email: z.string().email('Invalid email').optional().or(z.literal('')),
})

type CreateUserFormValues = z.infer<typeof createUserSchema>

const assignRoleSchema = z.object({
  role_name: z.string().min(1, 'Select a role'),
  enclave_id: z.string().optional(),
})

type AssignRoleFormValues = z.infer<typeof assignRoleSchema>

// ── Component ────────────────────────────────────────────────────────

export default function Users(): React.ReactElement {
  const { data: users = [], isLoading, error: queryError } = useUsers()
  const { data: enclaves = [] } = useEnclaves()
  const createUserMut = useCreateUser()
  const deleteUserMut = useDeleteUser()
  const assignRoleMut = useAssignRole()
  const removeRoleMut = useRemoveRole()

  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [roleDialogUserId, setRoleDialogUserId] = useState<string | null>(null)
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })

  // Create user form
  const {
    register: regCreate,
    handleSubmit: handleCreateSubmit,
    reset: resetCreate,
    formState: { errors: createErrors },
  } = useForm<CreateUserFormValues>({
    resolver: zodResolver(createUserSchema),
    defaultValues: { username: '', password: '', email: '' },
  })

  // Assign role form
  const {
    register: regRole,
    handleSubmit: handleRoleSubmit,
    reset: resetRole,
    formState: { errors: roleErrors },
  } = useForm<AssignRoleFormValues>({
    resolver: zodResolver(assignRoleSchema),
    defaultValues: { role_name: '', enclave_id: '' },
  })

  const showSnack = (message: string, severity: 'success' | 'error') => {
    setSnackbar({ open: true, message, severity })
  }

  const onCreateUser = async (values: CreateUserFormValues) => {
    try {
      await createUserMut.mutateAsync({
        username: values.username,
        password: values.password,
        email: values.email || undefined,
      })
      showSnack('User created.', 'success')
      resetCreate()
      setCreateDialogOpen(false)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to create user.'
      showSnack(msg, 'error')
    }
  }

  const handleDeleteUser = async (id: string) => {
    if (!window.confirm('Delete this user?')) return
    try {
      await deleteUserMut.mutateAsync(id)
      showSnack('User deleted.', 'success')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to delete user.'
      showSnack(msg, 'error')
    }
  }

  const onAssignRole = async (values: AssignRoleFormValues) => {
    if (!roleDialogUserId) return
    try {
      await assignRoleMut.mutateAsync({
        userId: roleDialogUserId,
        data: {
          role_name: values.role_name,
          enclave_id: values.enclave_id || undefined,
        },
      })
      showSnack('Role assigned.', 'success')
      resetRole()
      setRoleDialogUserId(null)
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to assign role.'
      showSnack(msg, 'error')
    }
  }

  const handleRemoveRole = async (userId: string, roleEnclaveId: string) => {
    try {
      await removeRoleMut.mutateAsync({ userId, roleEnclaveId })
      showSnack('Role removed.', 'success')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to remove role.'
      showSnack(msg, 'error')
    }
  }

  const roleDialogUser = users.find((u) => u.id === roleDialogUserId)

  return (
    <>
      <Card>
        <CardHeader
          title="Users"
          action={
            <Button variant="contained" startIcon={<AddIcon />} onClick={() => setCreateDialogOpen(true)}>
              Add User
            </Button>
          }
        />
        <CardContent>
          {queryError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to load users.
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
                  <TableCell>Username</TableCell>
                  <TableCell>Email</TableCell>
                  <TableCell>Roles</TableCell>
                  <TableCell>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} align="center">
                      <Typography color="text.secondary" variant="body2">
                        No users found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((u) => (
                    <TableRow key={u.id} hover>
                      <TableCell>
                        <Typography fontWeight={600}>{u.username}</Typography>
                      </TableCell>
                      <TableCell>{u.email || '--'}</TableCell>
                      <TableCell>
                        {u.role_assignments && u.role_assignments.length > 0 ? (
                          <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                            {u.role_assignments.map((ra) => (
                              <Chip
                                key={ra.id}
                                label={`${ra.role_name}${ra.enclave_name ? ` @ ${ra.enclave_name}` : ''}`}
                                color="info"
                                onDelete={() => handleRemoveRole(u.id, ra.id)}
                              />
                            ))}
                          </Stack>
                        ) : (
                          <Typography color="text.secondary" variant="body2">
                            None
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Stack direction="row" spacing={0.5}>
                          <Button
                            size="small"
                            variant="outlined"
                            color="success"
                            onClick={() => {
                              resetRole({ role_name: '', enclave_id: '' })
                              setRoleDialogUserId(u.id)
                            }}
                          >
                            + Role
                          </Button>
                          <Button
                            size="small"
                            variant="outlined"
                            color="error"
                            startIcon={<DeleteIcon fontSize="small" />}
                            onClick={() => handleDeleteUser(u.id)}
                          >
                            Delete
                          </Button>
                        </Stack>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create User Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create User</DialogTitle>
        <Box component="form" onSubmit={handleCreateSubmit(onCreateUser)} noValidate>
          <DialogContent>
            <TextField
              label="Username"
              {...regCreate('username')}
              error={!!createErrors.username}
              helperText={createErrors.username?.message}
              autoFocus
              sx={{ mb: 2 }}
            />
            <TextField
              label="Password"
              type="password"
              {...regCreate('password')}
              error={!!createErrors.password}
              helperText={createErrors.password?.message}
              sx={{ mb: 2 }}
            />
            <TextField
              label="Email"
              type="email"
              {...regCreate('email')}
              error={!!createErrors.email}
              helperText={createErrors.email?.message}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={createUserMut.isPending}>
              Create
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      {/* Assign Role Dialog */}
      <Dialog
        open={!!roleDialogUserId}
        onClose={() => setRoleDialogUserId(null)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Assign Role to {roleDialogUser?.username}</DialogTitle>
        <Box component="form" onSubmit={handleRoleSubmit(onAssignRole)} noValidate>
          <DialogContent>
            <TextField
              label="Role"
              select
              {...regRole('role_name')}
              error={!!roleErrors.role_name}
              helperText={roleErrors.role_name?.message}
              sx={{ mb: 2 }}
              defaultValue=""
            >
              <MenuItem value="">Select role...</MenuItem>
              <MenuItem value="admin">admin</MenuItem>
              <MenuItem value="operator">operator</MenuItem>
              <MenuItem value="viewer">viewer</MenuItem>
              <MenuItem value="auditor">auditor</MenuItem>
            </TextField>
            <TextField
              label="Enclave (optional)"
              select
              {...regRole('enclave_id')}
              defaultValue=""
            >
              <MenuItem value="">Global</MenuItem>
              {enclaves.map((enc) => (
                <MenuItem key={enc.id} value={enc.id}>
                  {enc.name}
                </MenuItem>
              ))}
            </TextField>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setRoleDialogUserId(null)}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={assignRoleMut.isPending}>
              Assign
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
