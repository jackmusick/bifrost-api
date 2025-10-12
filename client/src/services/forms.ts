/**
 * Forms API service
 */

import { api } from './api'
import type { Form, CreateFormRequest, UpdateFormRequest, FormSubmission, FormExecutionResponse } from '@/types/form'

export const formsService = {
  /**
   * Get all forms
   */
  async getForms(): Promise<Form[]> {
    return api.get<Form[]>('/forms')
  },

  /**
   * Get a specific form by ID
   * @param formId - Form ID
   * @param orgId - Organization ID (uses form's orgId to query correct partition)
   */
  async getForm(formId: string, orgId?: string): Promise<Form> {
    return api.request<Form>(`/forms/${formId}`, { method: 'GET', orgId })
  },

  /**
   * Create a new form
   */
  async createForm(request: CreateFormRequest): Promise<Form> {
    return api.post<Form>('/forms', request)
  },

  /**
   * Update a form
   * @param formId - Form ID
   * @param request - Update request
   * @param orgId - Organization ID (uses form's orgId to query correct partition)
   */
  async updateForm(formId: string, request: UpdateFormRequest, orgId?: string): Promise<Form> {
    return api.request<Form>(`/forms/${formId}`, {
      method: 'PUT',
      body: JSON.stringify(request),
      orgId
    })
  },

  /**
   * Delete a form
   * @param formId - Form ID
   * @param orgId - Organization ID (uses form's orgId to query correct partition)
   */
  async deleteForm(formId: string, orgId?: string): Promise<void> {
    return api.request<void>(`/forms/${formId}`, { method: 'DELETE', orgId })
  },

  /**
   * Activate a form
   */
  async activateForm(formId: string): Promise<Form> {
    return api.post<Form>(`/forms/${formId}/activate`, {})
  },

  /**
   * Deactivate a form
   */
  async deactivateForm(formId: string): Promise<Form> {
    return api.post<Form>(`/forms/${formId}/deactivate`, {})
  },

  /**
   * Submit a form to execute a workflow
   * @param submission - Form submission with formId, formData, and optional orgId
   */
  async submitForm(submission: FormSubmission & { orgId?: string }): Promise<FormExecutionResponse> {
    return api.request<FormExecutionResponse>(`/forms/${submission.formId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ form_data: submission.formData }),
      orgId: submission.orgId
    })
  },
}
