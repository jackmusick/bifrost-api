/**
 * React Query hooks for organization management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { organizationsService } from '@/services/organizations'
import type { CreateOrganizationRequest, UpdateOrganizationRequest } from '@/types/organization'
import { toast } from 'sonner'

export function useOrganizations() {
  return useQuery({
    queryKey: ['organizations'],
    queryFn: () => organizationsService.getOrganizations(),
    meta: {
      onError: (error: Error) => {
        toast.error('Failed to load organizations', {
          description: error.message,
        })
      },
    },
  })
}

export function useOrganization(orgId: string | undefined) {
  return useQuery({
    queryKey: ['organizations', orgId],
    queryFn: () => organizationsService.getOrganization(orgId!),
    enabled: !!orgId,
  })
}

export function useCreateOrganization() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateOrganizationRequest) => organizationsService.createOrganization(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      toast.success('Organization created', {
        description: 'The organization has been successfully created',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to create organization', {
        description: error.message,
      })
    },
  })
}

export function useUpdateOrganization() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ orgId, data }: { orgId: string; data: UpdateOrganizationRequest }) =>
      organizationsService.updateOrganization(orgId, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      queryClient.invalidateQueries({ queryKey: ['organizations', variables.orgId] })
      toast.success('Organization updated', {
        description: 'The organization has been successfully updated',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to update organization', {
        description: error.message,
      })
    },
  })
}

export function useDeleteOrganization() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (orgId: string) => organizationsService.deleteOrganization(orgId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['organizations'] })
      toast.success('Organization deleted', {
        description: 'The organization has been successfully deleted',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to delete organization', {
        description: error.message,
      })
    },
  })
}
