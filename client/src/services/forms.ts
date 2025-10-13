/**
 * Forms API service
 * All methods use the centralized api client which automatically handles
 * X-Organization-Id header from sessionStorage
 */

import { api } from './api'
import type { Form, CreateFormRequest, UpdateFormRequest, FormSubmission, FormExecutionResponse } from '@/types/form'

export const formsService = {
  /**
   * Get all forms
   * Organization context is handled automatically by the api client
   */
  async getForms(): Promise<Form[]> {
    return api.get<Form[]>('/forms')
  },

  /**
   * Get a specific form by ID
   * Organization context is handled automatically by the api client
   */
  async getForm(formId: string): Promise<Form> {
    return api.get<Form>(`/forms/${formId}`)
  },

  /**
   * Create a new form
   * Organization context is handled automatically by the api client
   */
  async createForm(request: CreateFormRequest): Promise<Form> {
    return api.post<Form>('/forms', request)
  },

  /**
   * Update a form
   * Organization context is handled automatically by the api client
   */
  async updateForm(formId: string, request: UpdateFormRequest): Promise<Form> {
    return api.put<Form>(`/forms/${formId}`, request)
  },

  /**
   * Delete a form
   * Organization context is handled automatically by the api client
   */
  async deleteForm(formId: string): Promise<void> {
    return api.delete<void>(`/forms/${formId}`)
  },

  /**
   * Activate a form
   * Organization context is handled automatically by the api client
   */
  async activateForm(formId: string): Promise<Form> {
    return api.post<Form>(`/forms/${formId}/activate`, {})
  },

  /**
   * Deactivate a form
   * Organization context is handled automatically by the api client
   */
  async deactivateForm(formId: string): Promise<Form> {
    return api.post<Form>(`/forms/${formId}/deactivate`, {})
  },

  /**
   * Submit a form to execute a workflow
   * Organization context is handled automatically by the api client
   */
  async submitForm(submission: FormSubmission): Promise<FormExecutionResponse> {
    return api.post<FormExecutionResponse>(`/forms/${submission.formId}/submit`, {
      form_data: submission.formData
    })
  },
}
