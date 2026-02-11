import { queuePendingNotification } from '../notifications/NotificationProvider'

const BOOTSTRAP_FLAG_KEY = 'nmia_bootstrap_required'

/** Check whether the bootstrap-required flag is set in localStorage. */
export function isBootstrapFlagged(): boolean {
  return localStorage.getItem(BOOTSTRAP_FLAG_KEY) === '1'
}

/** Set the bootstrap-required flag, queue a toast, and force redirect to login. */
export function handleBootstrapRequired(): void {
  localStorage.setItem(BOOTSTRAP_FLAG_KEY, '1')
  localStorage.removeItem('nmia_token')

  // Queue a notification that will survive the full page redirect.
  queuePendingNotification(
    'Target API requires bootstrap. You may be pointed at an uninitialized or wrong environment.',
    'warning',
  )

  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

/** Clear the bootstrap-required flag (e.g. after successful bootstrap or "show login anyway"). */
export function clearBootstrapFlag(): void {
  localStorage.removeItem(BOOTSTRAP_FLAG_KEY)
}
