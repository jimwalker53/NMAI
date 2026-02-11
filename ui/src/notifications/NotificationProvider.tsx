import React, { createContext, useCallback, useEffect, useState } from 'react'
import { Alert, AlertColor, Snackbar } from '@mui/material'

const PENDING_KEY = 'nmia_pending_notification'
const DEDUPE_KEY = 'nmia_notify_last_ts'
const DEDUPE_WINDOW_MS = 10_000
const AUTO_HIDE_MS = 6_000

export interface Notification {
  message: string
  severity: AlertColor
}

export interface NotifyContextValue {
  /** Show a snackbar notification. */
  notify: (message: string, severity?: AlertColor) => void
}

export const NotifyContext = createContext<NotifyContextValue>({
  notify: () => {},
})

/**
 * Queue a notification to be shown after the next full page load.
 * Used when a redirect via `window.location.href` is about to happen
 * and React state won't survive.
 */
export function queuePendingNotification(message: string, severity: AlertColor = 'warning'): void {
  const now = Date.now()
  const lastTs = Number(localStorage.getItem(DEDUPE_KEY) || '0')
  if (now - lastTs < DEDUPE_WINDOW_MS) return
  localStorage.setItem(DEDUPE_KEY, String(now))
  localStorage.setItem(PENDING_KEY, JSON.stringify({ message, severity }))
}

export default function NotificationProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [open, setOpen] = useState(false)
  const [current, setCurrent] = useState<Notification | null>(null)

  // On mount, check for a pending notification stored before a page redirect.
  useEffect(() => {
    const raw = localStorage.getItem(PENDING_KEY)
    if (raw) {
      localStorage.removeItem(PENDING_KEY)
      try {
        const parsed = JSON.parse(raw) as Notification
        setCurrent(parsed)
        setOpen(true)
      } catch {
        // corrupted value — ignore
      }
    }
  }, [])

  const notify = useCallback((message: string, severity: AlertColor = 'warning') => {
    const now = Date.now()
    const lastTs = Number(localStorage.getItem(DEDUPE_KEY) || '0')
    if (now - lastTs < DEDUPE_WINDOW_MS) return
    localStorage.setItem(DEDUPE_KEY, String(now))
    setCurrent({ message, severity })
    setOpen(true)
  }, [])

  const handleClose = (_event?: React.SyntheticEvent | Event, reason?: string) => {
    if (reason === 'clickaway') return
    setOpen(false)
  }

  return (
    <NotifyContext.Provider value={{ notify }}>
      {children}
      <Snackbar
        open={open}
        autoHideDuration={AUTO_HIDE_MS}
        onClose={handleClose}
        anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      >
        <Alert onClose={handleClose} severity={current?.severity ?? 'warning'} variant="filled" sx={{ width: '100%' }}>
          {current?.message}
        </Alert>
      </Snackbar>
    </NotifyContext.Provider>
  )
}
