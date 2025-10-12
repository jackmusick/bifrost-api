import { useAuth } from '@/hooks/useAuth'
import { NoAccess } from '@/components/NoAccess'

interface ProtectedRouteProps {
  children: React.ReactNode
  requirePlatformAdmin?: boolean
  requireOrgUser?: boolean
}

/**
 * Protected route component that checks user roles
 *
 * @param requirePlatformAdmin - Route requires PlatformAdmin role
 * @param requireOrgUser - Route requires OrgUser role (or PlatformAdmin)
 */
export function ProtectedRoute({
  children,
  requirePlatformAdmin = false,
  requireOrgUser = false
}: ProtectedRouteProps) {
  const { isPlatformAdmin, isOrgUser, isLoading } = useAuth()

  // Wait for auth to load
  if (isLoading) {
    return null
  }

  // Check for PlatformAdmin requirement
  if (requirePlatformAdmin && !isPlatformAdmin) {
    return <NoAccess />
  }

  // Check for OrgUser requirement (PlatformAdmin also has access)
  if (requireOrgUser && !isOrgUser && !isPlatformAdmin) {
    return <NoAccess />
  }

  return <>{children}</>
}
