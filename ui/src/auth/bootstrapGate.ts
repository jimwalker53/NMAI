const BOOTSTRAP_FLAG_KEY = 'nmia_bootstrap_required'

/** Check whether the bootstrap-required flag is set in localStorage. */
export function isBootstrapFlagged(): boolean {
  return localStorage.getItem(BOOTSTRAP_FLAG_KEY) === '1'
}

/** Set the bootstrap-required flag and force redirect to login. */
export function handleBootstrapRequired(): void {
  localStorage.setItem(BOOTSTRAP_FLAG_KEY, '1')
  localStorage.removeItem('nmia_token')
  if (window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

/** Clear the bootstrap-required flag (e.g. after successful bootstrap or "show login anyway"). */
export function clearBootstrapFlag(): void {
  localStorage.removeItem(BOOTSTRAP_FLAG_KEY)
}
