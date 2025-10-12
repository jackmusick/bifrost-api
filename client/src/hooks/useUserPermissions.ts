import { useQuery } from '@tanstack/react-query'
import { useAuth } from './useAuth'

interface UserDetails {
  id: string
  email: string
  displayName: string
  userType: 'PLATFORM' | 'ORG'
  isPlatformAdmin: boolean
  isActive: boolean
  lastLogin?: string
  createdAt: string
}

/**
 * Hook to fetch user details and permissions from the backend
 */
export function useUserPermissions() {
  const { user, isLoading: authLoading } = useAuth()

  const { data: userDetails, isLoading: detailsLoading, error } = useQuery<UserDetails>({
    queryKey: ['user', user?.userId],
    queryFn: async () => {
      if (!user?.userId) {
        throw new Error('No user ID available')
      }

      const response = await fetch(`/api/users/${user.userId}`)

      if (!response.ok) {
        // User doesn't exist in database - treat as unauthorized
        throw new Error('User not found in system')
      }

      return response.json()
    },
    enabled: !!user?.userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: false, // Don't retry on 404
  })

  return {
    userDetails,
    isPlatformAdmin: userDetails?.isPlatformAdmin ?? false,
    isOrgUser: userDetails?.userType === 'ORG',
    isLoading: authLoading || detailsLoading,
    error,
    hasAccess: !!userDetails && !error,
  }
}
