import React, { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
  Alert,
} from '@mui/material'
import { useAuth } from './AuthContext'

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
