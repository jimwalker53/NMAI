import React, { useEffect } from 'react'
import { useParams, Link as RouterLink } from 'react-router-dom'
import { useForm } from 'react-hook-form'
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
  Link,
  List,
  ListItem,
  ListItemText,
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
import {
  FindingRef,
  RiskFactor,
  useIdentity,
  useUpdateIdentity,
} from '../api/client'

// ── Helpers ──────────────────────────────────────────────────────────

function daysUntil(dateStr: string | undefined | null): number | null {
  if (!dateStr) return null
  const diff = new Date(dateStr).getTime() - new Date().getTime()
  return Math.ceil(diff / (1000 * 60 * 60 * 24))
}

function formatValue(val: unknown): string {
  if (val == null) return '--'
  if (Array.isArray(val)) return val.join(', ')
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return String(val)
}

function riskChipColor(score: number | null | undefined): 'error' | 'warning' | 'success' | 'default' {
  if (score == null) return 'default'
  if (score >= 70) return 'error'
  if (score >= 40) return 'warning'
  return 'success'
}

function expiryChipColor(days: number | null): 'error' | 'warning' | 'success' | 'default' {
  if (days == null) return 'default'
  if (days < 30) return 'error'
  if (days < 90) return 'warning'
  return 'success'
}

const SPECIAL_FIELDS = new Set(['owner', 'linked_system', 'sans', 'not_after', 'not_before', 'finding_ids'])

// ── Ownership form schema ────────────────────────────────────────────

const ownershipSchema = z.object({
  owner: z.string().optional(),
  linked_system: z.string().optional(),
})

type OwnershipFormValues = z.infer<typeof ownershipSchema>

// ── Component ────────────────────────────────────────────────────────

export default function IdentityDetail(): React.ReactElement {
  const { id } = useParams<{ id: string }>()
  const { data: identity, isLoading, error: queryError } = useIdentity(id!)
  const updateMut = useUpdateIdentity()

  const [snackbar, setSnackbar] = React.useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success',
  })

  const {
    register,
    handleSubmit,
    reset,
  } = useForm<OwnershipFormValues>({
    resolver: zodResolver(ownershipSchema),
    defaultValues: { owner: '', linked_system: '' },
  })

  // Sync form when identity loads
  useEffect(() => {
    if (identity) {
      const nd = (identity.normalized_data || identity) as Record<string, unknown>
      reset({
        owner: (nd.owner as string) || identity.owner || '',
        linked_system: (nd.linked_system as string) || identity.linked_system || '',
      })
    }
  }, [identity, reset])

  const onSave = async (values: OwnershipFormValues) => {
    try {
      await updateMut.mutateAsync({ id: id!, data: { owner: values.owner, linked_system: values.linked_system } })
      setSnackbar({ open: true, message: 'Identity updated.', severity: 'success' })
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Failed to update identity.'
      setSnackbar({ open: true, message: msg, severity: 'error' })
    }
  }

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
        <CircularProgress />
      </Box>
    )
  }

  if (queryError || !identity) {
    return <Alert severity="error">Identity not found.</Alert>
  }

  const nd = (identity.normalized_data || {}) as Record<string, unknown>
  const isCert = identity.type === 'cert' || identity.identity_type === 'cert'
  const expiry = (nd.not_after as string) || identity.not_after
  const daysLeft = daysUntil(expiry)
  const sans: (string | unknown)[] = (nd.sans as string[]) || identity.sans || []
  const findingIds: (FindingRef | string)[] = (nd.finding_ids as FindingRef[]) || identity.finding_ids || []
  const kvPairs = Object.entries(nd).filter(([k]) => !SPECIAL_FIELDS.has(k))
  const riskFactors = identity.risk_factors || identity.risk_breakdown || (nd.risk_factors as RiskFactor[] | Record<string, unknown> | undefined) || null

  return (
    <>
      {/* Breadcrumbs */}
      <Breadcrumbs sx={{ mb: 2 }}>
        <Link component={RouterLink} to="/identities" underline="hover" color="inherit">
          Identities
        </Link>
        <Typography color="text.primary">
          {(nd.display_name as string) || identity.display_name || 'Identity'}
        </Typography>
      </Breadcrumbs>

      {/* Header */}
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }} flexWrap="wrap" useFlexGap>
        <Typography variant="body2" color="text.secondary">
          Type: <strong>{identity.type || identity.identity_type || '--'}</strong>
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Enclave: <strong>{identity.enclave_name || identity.enclave_id || '--'}</strong>
        </Typography>
        <Chip
          label={identity.risk_score != null ? `Risk: ${identity.risk_score}` : 'Risk: --'}
          color={riskChipColor(identity.risk_score)}
          variant="filled"
        />
      </Stack>

      {/* Ownership */}
      <Card sx={{ mb: 2 }}>
        <CardHeader title="Ownership" />
        <CardContent>
          <Box component="form" onSubmit={handleSubmit(onSave)} noValidate>
            <Stack direction="row" spacing={2} alignItems="flex-start" flexWrap="wrap" useFlexGap>
              <TextField
                label="Owner"
                {...register('owner')}
                placeholder="Assign an owner..."
                sx={{ minWidth: 200, flex: 1 }}
              />
              <TextField
                label="Linked System"
                {...register('linked_system')}
                placeholder="e.g. Jenkins, Terraform..."
                sx={{ minWidth: 200, flex: 1 }}
              />
              <Button
                type="submit"
                variant="contained"
                disabled={updateMut.isPending}
                sx={{ alignSelf: 'center' }}
              >
                {updateMut.isPending ? 'Saving...' : 'Save'}
              </Button>
            </Stack>
          </Box>
        </CardContent>
      </Card>

      {/* Certificate Details */}
      {isCert && (
        <Card sx={{ mb: 2 }}>
          <CardHeader title="Certificate Details" />
          <CardContent>
            {expiry && (
              <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                <Typography variant="body2">
                  <strong>Expiration:</strong> {new Date(expiry).toLocaleDateString()}
                </Typography>
                {daysLeft != null && (
                  <Chip
                    label={daysLeft > 0 ? `${daysLeft} days remaining` : 'EXPIRED'}
                    color={expiryChipColor(daysLeft)}
                  />
                )}
              </Stack>
            )}
            {(nd.not_before as string) && (
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Not Before:</strong> {new Date(nd.not_before as string).toLocaleDateString()}
              </Typography>
            )}
            {sans.length > 0 && (
              <Box>
                <Typography variant="body2" fontWeight={600}>
                  Subject Alternative Names:
                </Typography>
                <List dense disablePadding>
                  {(Array.isArray(sans) ? sans : [sans]).map((san, idx) => (
                    <ListItem key={idx} disableGutters sx={{ pl: 2 }}>
                      <ListItemText primary={String(san)} primaryTypographyProps={{ variant: 'body2' }} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </CardContent>
        </Card>
      )}

      {/* Risk Assessment */}
      <Card sx={{ mb: 2 }}>
        <CardHeader title="Risk Assessment" />
        <CardContent>
          <Stack direction="row" spacing={1} alignItems="baseline" sx={{ mb: 2 }}>
            <Typography variant="h4" color={
              identity.risk_score != null && identity.risk_score >= 70
                ? 'error.main'
                : identity.risk_score != null && identity.risk_score >= 40
                  ? 'warning.main'
                  : 'success.main'
            }>
              {identity.risk_score != null ? identity.risk_score : '--'}
            </Typography>
            <Typography variant="body2" color="text.secondary">/ 100</Typography>
          </Stack>

          {riskFactors ? (
            <Box>
              <Typography variant="body2" fontWeight={600} sx={{ mb: 0.5 }}>
                Contributing Factors:
              </Typography>
              {Array.isArray(riskFactors) ? (
                <List dense disablePadding>
                  {(riskFactors as RiskFactor[]).map((f, idx) => (
                    <ListItem key={idx} disableGutters sx={{ pl: 2 }}>
                      <ListItemText
                        primary={typeof f === 'string' ? (f as string) : `${f.factor || f.name}: +${f.score || f.weight}`}
                        primaryTypographyProps={{ variant: 'body2' }}
                      />
                    </ListItem>
                  ))}
                </List>
              ) : typeof riskFactors === 'object' ? (
                <Table size="small">
                  <TableBody>
                    {Object.entries(riskFactors as Record<string, unknown>).map(([k, v]) => (
                      <TableRow key={k}>
                        <TableCell sx={{ fontWeight: 500, color: 'text.secondary', width: 180 }}>{k}</TableCell>
                        <TableCell>{formatValue(v)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <Typography variant="body2">{String(riskFactors)}</Typography>
              )}
            </Box>
          ) : (
            <Typography variant="body2" color="text.secondary">
              Risk score factors are computed based on: missing owner, missing linked system,
              certificate expiration proximity, stale last-seen date, and elevated privileges.
            </Typography>
          )}
        </CardContent>
      </Card>

      {/* Normalized Data */}
      <Card sx={{ mb: 2 }}>
        <CardHeader title="Normalized Data" />
        <CardContent>
          {kvPairs.length === 0 ? (
            <Typography color="text.secondary" variant="body2">
              No additional data fields.
            </Typography>
          ) : (
            <Table size="small">
              <TableBody>
                {kvPairs.map(([key, val]) => (
                  <TableRow key={key}>
                    <TableCell
                      sx={{ fontWeight: 500, color: 'text.secondary', width: 180, verticalAlign: 'top' }}
                    >
                      {key}
                    </TableCell>
                    <TableCell sx={{ wordBreak: 'break-word' }}>
                      {typeof val === 'object' && val !== null ? (
                        <Box
                          component="pre"
                          sx={{ m: 0, whiteSpace: 'pre-wrap', fontSize: '0.8rem', fontFamily: 'monospace' }}
                        >
                          {JSON.stringify(val, null, 2)}
                        </Box>
                      ) : (
                        formatValue(val)
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Provenance */}
      {findingIds.length > 0 && (
        <Card sx={{ mb: 2 }}>
          <CardHeader title="Provenance" />
          <CardContent>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Finding ID</TableCell>
                  <TableCell>Timestamp</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {findingIds.map((f, idx) => {
                  const fid = typeof f === 'object' ? (f as FindingRef).id || (f as FindingRef).finding_id : f
                  const ts = typeof f === 'object' ? (f as FindingRef).timestamp || (f as FindingRef).created_at : null
                  return (
                    <TableRow key={idx}>
                      <TableCell sx={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{fid}</TableCell>
                      <TableCell>{ts ? new Date(ts).toLocaleString() : '--'}</TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

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
