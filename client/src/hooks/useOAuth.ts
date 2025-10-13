/**
 * React Query hooks for OAuth connections
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { oauthService } from '@/services/oauth'
import type {
  CreateOAuthConnectionRequest,
  UpdateOAuthConnectionRequest,
} from '@/types/oauth'

// Query keys
export const oauthKeys = {
  all: ['oauth'] as const,
  lists: () => [...oauthKeys.all, 'list'] as const,
  list: (orgId?: string) => [...oauthKeys.lists(), { orgId }] as const,
  details: () => [...oauthKeys.all, 'detail'] as const,
  detail: (name: string, orgId?: string) => [...oauthKeys.details(), name, { orgId }] as const,
}

/**
 * List OAuth connections
 * Always includes GLOBAL connections as fallback
 */
export function useOAuthConnections(orgId?: string) {
  return useQuery({
    queryKey: oauthKeys.list(orgId),
    queryFn: () => oauthService.listConnections(orgId),
  })
}

/**
 * Get OAuth connection details
 */
export function useOAuthConnection(connectionName: string, orgId?: string) {
  return useQuery({
    queryKey: oauthKeys.detail(connectionName, orgId),
    queryFn: () => oauthService.getConnection(connectionName, orgId),
    enabled: !!connectionName,
  })
}

/**
 * Create OAuth connection
 */
export function useCreateOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      data,
      orgId,
    }: {
      data: CreateOAuthConnectionRequest
      orgId?: string | undefined
    }) => oauthService.createConnection(data, orgId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: oauthKeys.lists() })
      toast.success(`Connection "${variables.data.connection_name}" created successfully`)
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to create OAuth connection')
    },
  })
}

/**
 * Update OAuth connection
 */
export function useUpdateOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      connectionName,
      data,
      orgId,
    }: {
      connectionName: string
      data: UpdateOAuthConnectionRequest
      orgId?: string | undefined
    }) => oauthService.updateConnection(connectionName, data, orgId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: oauthKeys.lists() })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(variables.connectionName, variables.orgId),
      })
      toast.success(`Connection "${variables.connectionName}" updated successfully`)
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to update OAuth connection')
    },
  })
}

/**
 * Delete OAuth connection
 */
export function useDeleteOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ connectionName, orgId }: { connectionName: string; orgId?: string | undefined }) =>
      oauthService.deleteConnection(connectionName, orgId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: oauthKeys.lists() })
      toast.success(`Connection "${variables.connectionName}" deleted successfully`)
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to delete OAuth connection')
    },
  })
}

/**
 * Authorize OAuth connection (initiate OAuth flow)
 */
export function useAuthorizeOAuthConnection() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ connectionName, orgId }: { connectionName: string; orgId?: string | undefined }) =>
      oauthService.authorize(connectionName, orgId),
    onSuccess: (response, variables) => {
      // Invalidate to show updated status
      queryClient.invalidateQueries({ queryKey: oauthKeys.lists() })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(variables.connectionName, variables.orgId),
      })

      // Log the authorization URL for debugging
      console.log('OAuth Authorization URL:', response.authorization_url)

      // Open authorization URL in new window
      window.open(response.authorization_url, '_blank', 'width=600,height=700')

      toast.success('Authorization started - complete it in the popup window')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to start authorization')
    },
  })
}

/**
 * Cancel OAuth authorization (reset to not_connected status)
 */
export function useCancelOAuthAuthorization() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ connectionName, orgId }: { connectionName: string; orgId?: string | undefined }) =>
      oauthService.cancelAuthorization(connectionName, orgId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: oauthKeys.lists() })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(variables.connectionName, variables.orgId),
      })
      toast.success('Authorization canceled')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to cancel authorization')
    },
  })
}

/**
 * Manually refresh OAuth access token using refresh token
 */
export function useRefreshOAuthToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ connectionName, orgId }: { connectionName: string; orgId?: string | undefined }) =>
      oauthService.refreshToken(connectionName, orgId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: oauthKeys.lists() })
      queryClient.invalidateQueries({
        queryKey: oauthKeys.detail(variables.connectionName, variables.orgId),
      })
      toast.success('OAuth token refreshed successfully')
    },
    onError: (error: any) => {
      toast.error(error.message || 'Failed to refresh OAuth token')
    },
  })
}

/**
 * Get OAuth credentials (for debugging/admin purposes)
 */
export function useOAuthCredentials(connectionName: string, orgId?: string) {
  return useQuery({
    queryKey: [...oauthKeys.detail(connectionName, orgId), 'credentials'],
    queryFn: () => oauthService.getCredentials(connectionName, orgId),
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
