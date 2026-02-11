import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
} from '@mui/material'
import RefreshIcon from '@mui/icons-material/Refresh'
import { useAuth } from './AuthContext'
import { useBootstrapStatus } from '../api/client'
import { isBootstrapFlagged, clearBootstrapFlag } from './bootstrapGate'

const loginSchema = z.object({
  username: z.string().min(1, 'Required'),
  password: z.string().min(1, 'Required'),
})

type LoginFormValues = z.infer<typeof loginSchema>

interface AxiosErrorResponse {
  response?: {
    data?: {
      detail?: string
    }
  }
}

export default function Login(): React.ReactElement {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [showLoginAnyway, setShowLoginAnyway] = useState(false)

  const {
    data: bootstrapData,
    isError: bootstrapError,
    refetch: refetchBootstrap,
  } = useBootstrapStatus(!isAuthenticated)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { username: '', password: '' },
  })

  if (isAuthenticated) {
    return <Navigate to="/identities" replace />
  }

  const onSubmit = async (values: LoginFormValues): Promise<void> => {
    setError('')
    setLoading(true)
    try {
      clearBootstrapFlag()
      await login(values.username, values.password)
      navigate('/identities', { replace: true })
    } catch (err: unknown) {
      const axiosErr = err as AxiosErrorResponse
      const msg = axiosErr.response?.data?.detail || 'Login failed. Check your credentials.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  // Show bootstrap card if API says so OR if the interceptor flagged it
  const bootstrapRequired =
    bootstrapData?.bootstrap_required === true || isBootstrapFlagged()

  // ── Bootstrap-required gate ────────────────────────────────────────
  if (bootstrapRequired && !showLoginAnyway) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100vh',
          bgcolor: 'background.default',
        }}
      >
        <Container maxWidth="sm">
          <Paper sx={{ p: 4 }} elevation={4}>
            <Typography variant="h4" align="center" gutterBottom>
              NMIA
            </Typography>
            <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 3 }}>
              Non-Human Identity Authority
            </Typography>

            <Alert severity="warning" sx={{ mb: 3 }}>
              No admin account exists yet. Run the bootstrap commands below to get started.
            </Alert>

            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              1. Run database migrations
            </Typography>
            <Box
              component="pre"
              sx={{
                bgcolor: 'grey.900',
                color: 'grey.100',
                p: 1.5,
                borderRadius: 1,
                fontSize: '0.85rem',
                fontFamily: 'monospace',
                overflow: 'auto',
                mb: 2,
              }}
            >
              make migrate
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              2. Create the admin account (interactive password prompt)
            </Typography>
            <Box
              component="pre"
              sx={{
                bgcolor: 'grey.900',
                color: 'grey.100',
                p: 1.5,
                borderRadius: 1,
                fontSize: '0.85rem',
                fontFamily: 'monospace',
                overflow: 'auto',
                mb: 2,
              }}
            >
              make bootstrap
            </Box>

            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              3. (Optional) Seed sample data
            </Typography>
            <Box
              component="pre"
              sx={{
                bgcolor: 'grey.900',
                color: 'grey.100',
                p: 1.5,
                borderRadius: 1,
                fontSize: '0.85rem',
                fontFamily: 'monospace',
                overflow: 'auto',
                mb: 3,
              }}
            >
              make seed
            </Box>

            <Box sx={{ display: 'flex', gap: 1 }}>
              <Button
                variant="contained"
                startIcon={<RefreshIcon />}
                onClick={() => refetchBootstrap()}
              >
                Refresh
              </Button>
              <Button
                variant="text"
                onClick={() => { clearBootstrapFlag(); setShowLoginAnyway(true) }}
              >
                Show login anyway
              </Button>
            </Box>
          </Paper>
        </Container>
      </Box>
    )
  }

  // ── Normal login form ──────────────────────────────────────────────
  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        bgcolor: 'background.default',
      }}
    >
      <Container maxWidth="xs">
        <Paper sx={{ p: 4 }} elevation={4}>
          <Typography variant="h4" align="center" gutterBottom>
            NMIA
          </Typography>
          <Typography
            variant="body2"
            align="center"
            color="text.secondary"
            sx={{ mb: 3 }}
          >
            Non-Human Identity Authority
          </Typography>

          {bootstrapError && (
            <Alert severity="info" sx={{ mb: 2 }}>
              Could not check bootstrap status.
            </Alert>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
            <TextField
              label="Username"
              {...register('username')}
              error={!!errors.username}
              helperText={errors.username?.message}
              autoFocus
              sx={{ mb: 2 }}
            />
            <TextField
              label="Password"
              type="password"
              {...register('password')}
              error={!!errors.password}
              helperText={errors.password?.message}
              sx={{ mb: 2 }}
            />
            <Button
              type="submit"
              variant="contained"
              fullWidth
              disabled={loading}
              size="medium"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  )
}
