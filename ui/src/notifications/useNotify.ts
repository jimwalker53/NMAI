import { useContext } from 'react'
import { NotifyContext, NotifyContextValue } from './NotificationProvider'

/**
 * Hook to access the global notification system from within a React component.
 *
 * Usage:
 *   const { notify } = useNotify()
 *   notify('Something happened', 'warning')
 */
export function useNotify(): NotifyContextValue {
  return useContext(NotifyContext)
}
