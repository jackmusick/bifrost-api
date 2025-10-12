/**
 * React Query hooks for forms management
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { formsService } from '@/services/forms'
import type { CreateFormRequest, UpdateFormRequest, FormSubmission } from '@/types/form'
import { toast } from 'sonner'
import { useUser } from '@/contexts/UserContext'

export function useForms(orgId?: string | undefined) {
  return useQuery({
    queryKey: ['forms', orgId],
    queryFn: () => formsService.getForms(orgId !== undefined ? { orgId } : undefined),
  })
}

export function useForm(formId: string | undefined) {
  const { orgId } = useUser()

  return useQuery({
    queryKey: ['forms', formId, orgId],
    queryFn: () => formsService.getForm(formId!, orgId!),
    enabled: !!formId && !!orgId,
  })
}

export function useCreateForm() {
  const queryClient = useQueryClient()
  const { orgId } = useUser()

  return useMutation({
    mutationFn: (request: CreateFormRequest) => formsService.createForm(request, orgId!),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['forms'] })
      toast.success('Form created', {
        description: `Form "${variables.name}" has been created`,
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to create form', {
        description: error.message,
      })
    },
  })
}

export function useUpdateForm() {
  const queryClient = useQueryClient()
  const { orgId } = useUser()

  return useMutation({
    mutationFn: ({ formId, request }: { formId: string; request: UpdateFormRequest }) =>
      formsService.updateForm(formId, request, orgId!),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['forms'] })
      queryClient.invalidateQueries({ queryKey: ['forms', variables.formId] })
      toast.success('Form updated', {
        description: 'The form has been updated successfully',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to update form', {
        description: error.message,
      })
    },
  })
}

export function useDeleteForm() {
  const queryClient = useQueryClient()
  const { orgId } = useUser()

  return useMutation({
    mutationFn: (formId: string) => formsService.deleteForm(formId, orgId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] })
      toast.success('Form deleted', {
        description: 'The form has been removed',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to delete form', {
        description: error.message,
      })
    },
  })
}

export function useActivateForm() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (formId: string) => formsService.activateForm(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] })
      toast.success('Form activated', {
        description: 'The form is now active and available',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to activate form', {
        description: error.message,
      })
    },
  })
}

export function useDeactivateForm() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (formId: string) => formsService.deactivateForm(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['forms'] })
      toast.success('Form deactivated', {
        description: 'The form is now inactive',
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to deactivate form', {
        description: error.message,
      })
    },
  })
}

export function useSubmitForm() {
  return useMutation({
    mutationFn: (submission: FormSubmission & { orgId?: string }) => formsService.submitForm(submission),
    onSuccess: (data) => {
      toast.success('Workflow execution started', {
        description: `Execution ID: ${data.executionId}`,
      })
    },
    onError: (error: Error) => {
      toast.error('Failed to submit form', {
        description: error.message,
      })
    },
  })
}
