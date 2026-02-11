import { createTheme } from '@mui/material/styles'

export const theme = createTheme({
  palette: {
    primary: { main: '#4361ee' },
    secondary: { main: '#1a1a2e' },
    success: { main: '#2ec4b6' },
    warning: { main: '#f4a261' },
    error: { main: '#e63946' },
    background: { default: '#f0f2f5', paper: '#ffffff' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h4: { fontWeight: 700 },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
  },
  components: {
    MuiButton: {
      defaultProps: { disableElevation: true, size: 'small' },
      styleOverrides: { root: { textTransform: 'none' } },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          fontWeight: 700,
          textTransform: 'uppercase',
          fontSize: '0.75rem',
          color: '#666',
        },
      },
    },
    MuiCard: { defaultProps: { variant: 'outlined' } },
    MuiChip: { defaultProps: { size: 'small' } },
    MuiTextField: { defaultProps: { size: 'small', fullWidth: true } },
  },
})
