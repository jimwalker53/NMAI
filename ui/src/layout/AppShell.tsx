import React from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  AppBar,
  Box,
  Button,
  Container,
  IconButton,
  Toolbar,
  Typography,
  Tab,
  Tabs,
} from '@mui/material'
import LogoutIcon from '@mui/icons-material/Logout'
import SecurityIcon from '@mui/icons-material/Security'
import CableIcon from '@mui/icons-material/Cable'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import AssessmentIcon from '@mui/icons-material/Assessment'
import PeopleIcon from '@mui/icons-material/People'
import { useAuth } from '../auth/AuthContext'

const NAV_ITEMS = [
  { label: 'Identities', path: '/identities', icon: <SecurityIcon fontSize="small" /> },
  { label: 'Connectors', path: '/connectors', icon: <CableIcon fontSize="small" /> },
  { label: 'Enclaves', path: '/enclaves', icon: <AccountTreeIcon fontSize="small" /> },
  { label: 'Reports', path: '/reports', icon: <AssessmentIcon fontSize="small" /> },
]

const ADMIN_ITEM = { label: 'Users', path: '/users', icon: <PeopleIcon fontSize="small" /> }

export default function AppShell(): React.ReactElement {
  const { isAdmin, user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const items = isAdmin ? [...NAV_ITEMS, ADMIN_ITEM] : NAV_ITEMS

  // Determine which tab is currently active
  const currentTab = items.findIndex((item) =>
    location.pathname.startsWith(item.path),
  )

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    navigate(items[newValue].path)
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="sticky" sx={{ bgcolor: 'secondary.main' }}>
        <Toolbar variant="dense" sx={{ gap: 2 }}>
          <Typography
            variant="h6"
            sx={{ fontWeight: 700, letterSpacing: '0.05em', color: '#4cc9f0', mr: 2, cursor: 'pointer' }}
            onClick={() => navigate('/')}
          >
            NMIA
          </Typography>

          <Tabs
            value={currentTab >= 0 ? currentTab : false}
            onChange={handleTabChange}
            textColor="inherit"
            TabIndicatorProps={{ sx: { bgcolor: '#4cc9f0' } }}
            sx={{
              flexGrow: 1,
              '& .MuiTab-root': {
                minHeight: 48,
                textTransform: 'none',
                fontSize: '0.875rem',
                color: '#ccc',
                '&.Mui-selected': { color: '#fff' },
              },
            }}
          >
            {items.map((item) => (
              <Tab key={item.path} icon={item.icon} iconPosition="start" label={item.label} />
            ))}
          </Tabs>

          <Typography variant="body2" sx={{ color: '#aaa', whiteSpace: 'nowrap' }}>
            {user?.sub || user?.username || 'User'}
          </Typography>

          <IconButton size="small" onClick={logout} sx={{ color: '#ccc', '&:hover': { color: '#f72585' } }}>
            <LogoutIcon fontSize="small" />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ py: 3, flex: 1 }}>
        <Outlet />
      </Container>
    </Box>
  )
}
