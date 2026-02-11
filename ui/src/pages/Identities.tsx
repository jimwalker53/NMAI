import React, { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert,
  Box,
  Button,
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
  TablePagination,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import FilterListIcon from '@mui/icons-material/FilterList'
import {
  IdentityQueryParams,
  useIdentities,
  useEnclaves,
} from '../api/client'

const PAGE_SIZE = 25

function riskChipColor(score: number | null | undefined): 'error' | 'warning' | 'success' | 'default' {
  if (score == null) return 'default'
  if (score >= 70) return 'error'
  if (score >= 40) return 'warning'
  return 'success'
}

export default function Identities(): React.ReactElement {
  const navigate = useNavigate()
  const { data: enclaves = [] } = useEnclaves()

  // Filter state
  const [enclaveFilter, setEnclaveFilter] = useState('')
  const [typeFilter, setTypeFilter] = useState('')
  const [search, setSearch] = useState('')
  const [riskMin, setRiskMin] = useState('')
  const [riskMax, setRiskMax] = useState('')
  const [page, setPage] = useState(0)

  // Applied filters (only update when user clicks Filter or changes page)
  const [appliedFilters, setAppliedFilters] = useState<IdentityQueryParams>({
    limit: PAGE_SIZE,
    offset: 0,
  })

  const params: IdentityQueryParams = useMemo(() => appliedFilters, [appliedFilters])

  const { data, isLoading, error: queryError } = useIdentities(params)
  const identities = data?.items ?? []
  const total = data?.total ?? 0

  const handleApplyFilters = () => {
    const newParams: IdentityQueryParams = { limit: PAGE_SIZE, offset: 0 }
    if (enclaveFilter) newParams.enclave_id = enclaveFilter
    if (typeFilter) newParams.type = typeFilter
    if (search) newParams.search = search
    if (riskMin !== '') newParams.risk_score_min = Number(riskMin)
    if (riskMax !== '') newParams.risk_score_max = Number(riskMax)
    setPage(0)
    setAppliedFilters(newParams)
  }

  const handlePageChange = (_event: unknown, newPage: number) => {
    setPage(newPage)
    setAppliedFilters((prev) => ({ ...prev, offset: newPage * PAGE_SIZE }))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleApplyFilters()
  }

  return (
    <Card>
      <CardHeader
        title="Identities"
        subheader={`${total} total`}
      />
      <CardContent>
        {/* Filter Bar */}
        <Stack direction="row" spacing={1.5} sx={{ mb: 2 }} flexWrap="wrap" useFlexGap alignItems="flex-end">
          <TextField
            label="Enclave"
            select
            value={enclaveFilter}
            onChange={(e) => setEnclaveFilter(e.target.value)}
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            {enclaves.map((enc) => (
              <MenuItem key={enc.id} value={enc.id}>
                {enc.name}
              </MenuItem>
            ))}
          </TextField>

          <TextField
            label="Type"
            select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            sx={{ minWidth: 150 }}
          >
            <MenuItem value="">All</MenuItem>
            <MenuItem value="svc_acct">Service Account</MenuItem>
            <MenuItem value="cert">Certificate</MenuItem>
            <MenuItem value="api_key">API Key</MenuItem>
            <MenuItem value="bot">Bot</MenuItem>
          </TextField>

          <TextField
            label="Search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Name, owner..."
            sx={{ minWidth: 180 }}
          />

          <TextField
            label="Risk Min"
            type="number"
            value={riskMin}
            onChange={(e) => setRiskMin(e.target.value)}
            onKeyDown={handleKeyDown}
            inputProps={{ min: 0, max: 100 }}
            sx={{ width: 100 }}
          />

          <TextField
            label="Risk Max"
            type="number"
            value={riskMax}
            onChange={(e) => setRiskMax(e.target.value)}
            onKeyDown={handleKeyDown}
            inputProps={{ min: 0, max: 100 }}
            sx={{ width: 100 }}
          />

          <Button variant="contained" startIcon={<FilterListIcon />} onClick={handleApplyFilters}>
            Filter
          </Button>
        </Stack>

        {queryError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            Failed to load identities.
          </Alert>
        )}

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Display Name</TableCell>
                  <TableCell>Type</TableCell>
                  <TableCell>Enclave</TableCell>
                  <TableCell>Owner</TableCell>
                  <TableCell>Linked System</TableCell>
                  <TableCell>Risk Score</TableCell>
                  <TableCell>Last Seen</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {identities.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} align="center">
                      <Typography color="text.secondary" variant="body2">
                        No identities found.
                      </Typography>
                    </TableCell>
                  </TableRow>
                ) : (
                  identities.map((ident) => {
                    const nd = ident.normalized_data as Record<string, unknown> | undefined
                    return (
                      <TableRow
                        key={ident.id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => navigate(`/identities/${ident.id}`)}
                      >
                        <TableCell>
                          <Typography fontWeight={600}>
                            {ident.display_name || (nd?.display_name as string) || '--'}
                          </Typography>
                        </TableCell>
                        <TableCell>{ident.type || ident.identity_type || '--'}</TableCell>
                        <TableCell>{ident.enclave_name || ident.enclave_id || '--'}</TableCell>
                        <TableCell>{ident.owner || (nd?.owner as string) || '--'}</TableCell>
                        <TableCell>{ident.linked_system || (nd?.linked_system as string) || '--'}</TableCell>
                        <TableCell>
                          <Chip
                            label={ident.risk_score != null ? ident.risk_score : '--'}
                            color={riskChipColor(ident.risk_score)}
                            variant="filled"
                          />
                        </TableCell>
                        <TableCell>
                          {ident.last_seen ? new Date(ident.last_seen).toLocaleDateString() : '--'}
                        </TableCell>
                      </TableRow>
                    )
                  })
                )}
              </TableBody>
            </Table>

            <TablePagination
              component="div"
              count={total}
              page={page}
              onPageChange={handlePageChange}
              rowsPerPage={PAGE_SIZE}
              rowsPerPageOptions={[PAGE_SIZE]}
            />
          </>
        )}
      </CardContent>
    </Card>
  )
}
