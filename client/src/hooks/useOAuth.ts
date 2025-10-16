/**
 * React Query hooks for OAuth connections
 * All hooks use the centralized api client which handles X-Organization-Id automatically
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { oauthService } from '@/services/oauth'
import type { components } from '@/lib/v1'
import { useScopeStore } from '@/stores/scopeStore'
type CreateOAuthConnectionRequest = components['schemas']['CreateOAuthConnectionRequest']
type UpdateOAuthConnectionRequest = components['schemas']['UpdateOAuthConnectionRequest']

// Query keys
export const oauthKeys = {
  all: ['oauth'] as const,
  lists: (orgId?: string | null) => [...oauthKeys.all, 'list', orgId] as const,
  list: (orgId?: string | null) => [...oauthKeys.lists(orgId)] as const,
  details: () => [...oauthKeys.all, 'detail'] as const,
  detail: (name: string) => [...oauthKeys.details(), name] as const,
}

/**
 * List OAuth connections
 * Organization context is handled automatically by the api client
 * Always includes GLOBAL connections as fallback
 */
export function useOAuthConnections() {
  const orgId = useScopeStore((state) => state.scope.orgId)
  const hasHydrated = useScopeStore((state) => state._hasHydrated)

  return useQuery<components['schemas']['OAuthConnection'][]>({
    queryKey: oauthKeys.list(orgId),
    queryFn: async () => {
      const result = await oauthService.listConnections()
      return result as unknown as components['schemas']['OAuthConnection'][]
    },
    // Wait for Zustand to rehydrate from localStorage before making API calls
    enabled: hasHydrated,
    // Don't use cached data from previous scope
    staleTime: 0,
  })
}

/**
 * Get OAuth connection details
 * Organization context is handled automatically by the api client
 */
export function useOAuthConnection(connectionName: string) {
  return useQuery({
    queryKey: oauthKeys.detail(connectionName),
    queryFn: () => oauthService.getConnection(connectionName),
    enabled: !!connectionName,
  })
}

/**
 * Create OAuth connection
 * Organization context is handled automatically by the api client
 */
export function useCreateOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateOAuthConnectionRequest) => oauthService.createConnection(data),
    onSuccess: (_, data) => {
      // Invalidate all OAuth list queries (for all scopes)
      queryClient.invalidateQueries({ queryKey: ['oauth', 'list'] })
      toast.success(`Connection "${data.connection_name}" created successfully`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to create OAuth connection')
    },
  })
}

/**
 * Update OAuth connection
 * Organization context is handled automatically by the api client
 */
export function useUpdateOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      connectionName,
      data,
    }: {
      connectionName: string
      data: UpdateOAuthConnectionRequest
    }) => oauthService.updateConnection(connectionName, data),
    onSuccess: (_, variables) => {
      // Invalidate all OAuth list queries (for all scopes)
      queryClient.invalidateQueries({ queryKey: ['oauth', 'list'] })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(variables.connectionName),
      })
      toast.success(`Connection "${variables.connectionName}" updated successfully`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to update OAuth connection')
    },
  })
}

/**
 * Delete OAuth connection
 * Organization context is handled automatically by the api client
 */
export function useDeleteOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (connectionName: string) => oauthService.deleteConnection(connectionName),
    onSuccess: (_, connectionName) => {
      // Invalidate all OAuth list queries (for all scopes)
      queryClient.invalidateQueries({ queryKey: ['oauth', 'list'] })
      toast.success(`Connection "${connectionName}" deleted successfully`)
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to delete OAuth connection')
    },
  })
}

/**
 * Authorize OAuth connection (initiate OAuth flow)
 * Organization context is handled automatically by the api client
 */
export function useAuthorizeOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (connectionName: string) => oauthService.authorize(connectionName),
    onSuccess: (response, connectionName) => {
      // Invalidate to show updated status
      // Invalidate all OAuth list queries (for all scopes)
      queryClient.invalidateQueries({ queryKey: ['oauth', 'list'] })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(connectionName),
      })

      // Log the authorization URL for debugging
      console.log('OAuth Authorization URL:', response.authorization_url)

      // Open authorization URL in new window
      window.open(response.authorization_url, '_blank', 'width=600,height=700')

      toast.success('Authorization started - complete it in the popup window')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to start authorization')
    },
  })
}

/**
 * Cancel OAuth authorization (reset to not_connected status)
 * Organization context is handled automatically by the api client
 */
export function useCancelOAuthAuthorization() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (connectionName: string) => oauthService.cancelAuthorization(connectionName),
    onSuccess: (_, connectionName) => {
      // Invalidate all OAuth list queries (for all scopes)
      queryClient.invalidateQueries({ queryKey: ['oauth', 'list'] })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(connectionName),
      })
      toast.success('Authorization canceled')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to cancel authorization')
    },
  })
}

/**
 * Manually refresh OAuth access token using refresh token
 * Organization context is handled automatically by the api client
 */
export function useRefreshOAuthToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (connectionName: string) => oauthService.refreshToken(connectionName),
    onSuccess: (_, connectionName) => {
      // Invalidate all OAuth list queries (for all scopes)
      queryClient.invalidateQueries({ queryKey: ['oauth', 'list'] })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(connectionName),
      })
      toast.success('OAuth token refreshed successfully')
    },
    onError: (error: Error) => {
      toast.error(error.message || 'Failed to refresh OAuth token')
    },
  })
}

/**
 * Get OAuth credentials (for debugging/admin purposes)
 * Organization context is handled automatically by the api client
 */
export function useOAuthCredentials(connectionName: string) {
  return useQuery({
    queryKey: [...oauthKeys.detail(connectionName), 'credentials'],
    queryFn: () => oauthService.getCredentials(connectionName),
    enabled: !!connectionName,
    // Don't retry on error - credentials might not be available
    retry: false,
  })
}

/**
 * Get OAuth refresh job status
 */
export function useOAuthRefreshJobStatus() {
  return useQuery({
    queryKey: [...oauthKeys.all, 'refresh-job-status'],
    queryFn: async () => {
      const response = await fetch('/api/oauth/refresh_job_status')
      if (!response.ok) {
        throw new Error('Failed to fetch refresh job status')
      }
      const data = await response.json()
      if (!data.last_run) {
        return null // Job hasn't run yet
      }
      return {
        ...data.last_run,
        updated_at: data.last_run.end_time || data.last_run.start_time,
      }
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}
