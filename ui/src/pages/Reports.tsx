import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useExpiringReport, useOrphanedReport } from '../api/client'

// ── Helpers ──────────────────────────────────────────────────────────

function daysUntil(dateStr: string | undefined | null): number | null {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - new Date().getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

function daysChipColor(days: number | null): 'error' | 'warning' | 'success' | 'default' {
  if (days == null) return 'default'
  if (days < 30) return 'error'
  if (days < 90) return 'warning'
  return 'success'
}

function riskChipColor(score: number | null | undefined): 'error' | 'warning' | 'success' | 'default' {
  if (score == null) return 'default'
  if (score >= 70) return 'error'
  if (score >= 40) return 'warning'
  return 'success'
}

// ── Component ────────────────────────────────────────────────────────

export default function Reports(): React.ReactElement {
  const navigate = useNavigate()
  const [expiringDays, setExpiringDays] = useState(90)

  const {
    data: expiringCerts = [],
    isLoading: expiringLoading,
    error: expiringError,
  } = useExpiringReport(expiringDays)

  const {
    data: orphaned = [],
    isLoading: orphanedLoading,
    error: orphanedError,
  } = useOrphanedReport()

  return (
    <Stack spacing={2}>
      {/* Expiring Certificates */}
      <Card>
        <CardHeader
          title="Expiring Certificates"
          action={
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="body2" color="text.secondary">
                Expiring within
              </Typography>
              <TextField
                select
                value={expiringDays}
                onChange={(e) => setExpiringDays(Number(e.target.value))}
                sx={{ width: 130 }}
              >
                <MenuItem value={30}>30 days</MenuItem>
                <MenuItem value={60}>60 days</MenuItem>
                <MenuItem value={90}>90 days</MenuItem>
                <MenuItem value={180}>180 days</MenuItem>
              </TextField>
            </Stack>
          }
        />
        <CardContent>
          {expiringError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to load expiring certificates report.
            </Alert>
          )}

          {expiringLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Name</TableCell>
                  <TableCell>Enclave</TableCell>
                  <TableCell>Expiration</TableCell>
                  <TableCell>Days Remaining</TableCell>
                  <TableCell>Risk Score</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {expiringCerts.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" variant="body2">
                        No expiring certificates found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  expiringCerts.map((cert) => {
                    const nd = (cert.normalized_data || {}) as Record<string, unknown>
                    const expDate = cert.not_after || (nd.not_after as string)
                    const days = daysUntil(expDate)
                    return (
                      <TableRow
                        key={cert.id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/identities/${cert.id}`)}
                      >
                        <TableCell>
                          <Typography fontWeight={600}>
                            {cert.display_name || (nd.display_name as string) || '--'}
                          </Typography>
                        </TableCell>
                        <TableCell>{cert.enclave_name || cert.enclave_id || '--'}</TableCell>
                        <TableCell>
                          {expDate ? new Date(expDate).toLocaleDateString() : '--'}
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={days != null ? (days > 0 ? `${days} days` : 'EXPIRED') : '--'}
                            color={daysChipColor(days)}
                          />
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={cert.risk_score != null ? cert.risk_score : '--'}
                            color={riskChipColor(cert.risk_score)}
                            variant="filled"
                          />
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Orphaned Identities */}
      <Card>
        <CardHeader
          title="Orphaned Identities"
          subheader="Identities missing an owner or linked system"
        />
        <CardContent>
          {orphanedError && (
            <Alert severity="error" sx={{ mb: 2 }}>
              Failed to load orphaned identities report.
            </Alert>
          )}

          {orphanedLoading ? (
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
                  <TableCell>Missing</TableCell>
                  <TableCell>Risk Score</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {orphaned.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} align="center">
                      <Typography color="text.secondary" variant="body2">
                        No orphaned identities found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  orphaned.map((ident) => {
                    const nd = (ident.normalized_data || {}) as Record<string, unknown>
                    const hasOwner = !!(ident.owner || nd.owner)
                    const hasLinked = !!(ident.linked_system || nd.linked_system)
                    const missing: string[] = []
                    if (!hasOwner) missing.push('Owner')
                    if (!hasLinked) missing.push('Linked System')
                    return (
                      <TableRow
                        key={ident.id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/identities/${ident.id}`)}
                      >
                        <TableCell>
                          <Typography fontWeight={600}>
                            {ident.display_name || (nd.display_name as string) || '--'}
                          </Typography>
                        </TableCell>
                        <TableCell>{ident.type || ident.identity_type || '--'}</TableCell>
                        <TableCell>{ident.enclave_name || ident.enclave_id || '--'}</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={0.5}>
                            {missing.map((m) => (
                              <Chip key={m} label={m} color="error" variant="outlined" />
                            ))}
                          </Stack>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={ident.risk_score != null ? ident.risk_score : '--'}
                            color={riskChipColor(ident.risk_score)}
                            variant="filled"
                          />
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </Stack>
  )
}
