/**
 * Forms API service
 */

import { api } from './api'
import type { Form, CreateFormRequest, UpdateFormRequest, FormSubmission, FormExecutionResponse } from '@/types/form'

export const formsService = {
  /**
   * Get all forms
   */
  async getForms(params?: { orgId?: string }): Promise<Form[]> {
    return api.get<Form[]>('/forms', params as Record<string, string>)
  },

  /**
   * Get a specific form by ID
   */
  async getForm(formId: string, orgId: string): Promise<Form> {
    return api.get<Form>(`/forms/${formId}`, { orgId })
  },

  /**
   * Create a new form
   */
  async createForm(request: CreateFormRequest, orgId: string): Promise<Form> {
    return api.post<Form>('/forms', request, { orgId })
  },

  /**
   * Update a form
   */
  async updateForm(formId: string, request: UpdateFormRequest, orgId: string): Promise<Form> {
    return api.put<Form>(`/forms/${formId}`, request, { orgId })
  },

  /**
   * Delete a form
   */
  async deleteForm(formId: string, orgId: string): Promise<void> {
    return api.delete<void>(`/forms/${formId}`, { orgId })
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
   */
  async submitForm(submission: FormSubmission, orgId: string): Promise<FormExecutionResponse> {
    return api.post<FormExecutionResponse>(`/forms/${submission.formId}/submit`, {
      form_data: submission.formData,
    }, { orgId })
  },
}
