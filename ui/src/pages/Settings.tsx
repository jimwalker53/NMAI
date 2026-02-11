import React from 'react'
import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material'
import { useApiMeta, useCollectors, useEnclaves } from '../api/client'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '') as string
const isProxyMode = !API_BASE_URL

export default function Settings(): React.ReactElement {
  const { data: meta, isLoading: metaLoading, isError: metaError } = useApiMeta()
  const { data: enclaves = [], isLoading: enclavesLoading } = useEnclaves()
  const { data: collectors = [], isLoading: collectorsLoading } = useCollectors()

  return (
    <>
      <Typography variant="h5" sx={{ mb: 3 }}>Settings</Typography>

      {/* ── UI Configuration ──────────────────────────────────── */}
      <Card sx={{ mb: 3 }}>
        <CardHeader title="UI Configuration" />
        <CardContent>
          <Table size="small">
            <TableBody>
              <TableRow>
                <TableCell sx={{ fontWeight: 600, width: 200 }}>API Base URL</TableCell>
                <TableCell>
                  <code>{API_BASE_URL || '(empty — relative paths)'}</code>
                </TableCell>
              </TableRow>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Mode</TableCell>
                <TableCell>
                  <Chip
                    label={isProxyMode ? 'Proxy / Relative' : 'Absolute URL'}
                    color={isProxyMode ? 'info' : 'default'}
                    variant="outlined"
                    size="small"
                  />
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* ── API Info ──────────────────────────────────────────── */}
      <Card sx={{ mb: 3 }}>
        <CardHeader title="API Server" />
        <CardContent>
          {metaLoading && <Skeleton variant="rectangular" height={80} />}
          {metaError && (
            <Alert severity="warning">Could not reach the API meta endpoint.</Alert>
          )}
          {meta && (
            <Table size="small">
              <TableBody>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600, width: 200 }}>Service</TableCell>
                  <TableCell>{meta.service}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Version</TableCell>
                  <TableCell>{meta.version}</TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Build</TableCell>
                  <TableCell><code>{meta.build}</code></TableCell>
                </TableRow>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Server Time</TableCell>
                  <TableCell>{new Date(meta.time).toLocaleString()}</TableCell>
                </TableRow>
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ── Enclaves Summary ──────────────────────────────────── */}
      <Card sx={{ mb: 3 }}>
        <CardHeader
          title="Enclaves"
          action={
            !enclavesLoading && (
              <Chip label={`${enclaves.length} total`} size="small" variant="outlined" />
            )
          }
        />
        <CardContent>
          {enclavesLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
              <CircularProgress size={24} />
            </Box>
          ) : enclaves.length === 0 ? (
            <Typography color="text.secondary" variant="body2">No enclaves found.</Typography>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Description</TableCell>
                  <TableCell>Created</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {enclaves.map((e) => (
                  <TableRow key={e.id} hover>
                    <TableCell>{e.name}</TableCell>
                    <TableCell>{e.description || '--'}</TableCell>
                    <TableCell>{e.created_at ? new Date(e.created_at).toLocaleDateString() : '--'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ── Collectors ────────────────────────────────────────── */}
      <Card sx={{ mb: 3 }}>
        <CardHeader title="Collectors" />
        <CardContent>
          {collectorsLoading ? (
            <Skeleton variant="rectangular" height={60} />
          ) : collectors.length === 0 ? (
            <Alert severity="info" variant="outlined">
              No collectors registered yet. Once Windows collectors connect to this NMIA instance they will appear here.
            </Alert>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Version</TableCell>
                  <TableCell>Last Seen</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {collectors.map((c) => (
                  <TableRow key={c.id} hover>
                    <TableCell>{c.name || c.id}</TableCell>
                    <TableCell>{c.version || '--'}</TableCell>
                    <TableCell>{c.last_seen ? new Date(c.last_seen).toLocaleString() : '--'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </>
  )
}
