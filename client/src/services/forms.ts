/**
 * Forms API service - fully type-safe with openapi-fetch
 */

import { apiClient } from '@/lib/api-client'
import type { components } from '@/lib/v1'
import type { FormSubmission, FormExecutionResponse } from '@/lib/client-types'

export const formsService = {
  /**
   * Get all forms
   */
  async getForms() {
    const { data, error } = await apiClient.GET('/forms')
    if (error) throw new Error(`Failed to fetch forms: ${error}`)
    return data
  },

  /**
   * Get a specific form by ID
   */
  async getForm(formId: string) {
    const { data, error } = await apiClient.GET('/forms/{formId}', {
      params: { path: { formId } },
    })
    if (error) throw new Error(`Failed to fetch form: ${error}`)
    return data
  },

  /**
   * Create a new form
   */
  async createForm(request: components['schemas']['CreateFormRequest']) {
    const { data, error } = await apiClient.POST('/forms', {
      body: request,
    })
    if (error) throw new Error(`Failed to create form: ${error}`)
    return data
  },

  /**
   * Update a form
   */
  async updateForm(formId: string, request: components['schemas']['UpdateFormRequest']) {
    const { data, error } = await apiClient.PUT('/forms/{formId}', {
      params: { path: { formId } },
      body: request,
    })
    if (error) throw new Error(`Failed to update form: ${error}`)
    return data
  },

  /**
   * Delete a form
   */
  async deleteForm(formId: string) {
    const { data, error } = await apiClient.DELETE('/forms/{formId}', {
      params: { path: { formId } },
    })
    if (error) throw new Error(`Failed to delete form: ${error}`)
    return data
  },

  // TODO: These endpoints don't exist in the OpenAPI spec yet
  // Uncomment when backend endpoints are implemented
  // /**
  //  * Activate a form
  //  */
  // async activateForm(formId: string) {
  //   const { data, error } = await apiClient.POST('/forms/{formId}/activate', {
  //     params: { path: { formId } },
  //   })
  //   if (error) throw new Error(`Failed to activate form: ${error}`)
  //   return data
  // },

  // /**
  //  * Deactivate a form
  //  */
  // async deactivateForm(formId: string) {
  //   const { data, error } = await apiClient.POST('/forms/{formId}/deactivate', {
  //     params: { path: { formId } },
  //   })
  //   if (error) throw new Error(`Failed to deactivate form: ${error}`)
  //   return data
  // },

  /**
   * Execute a form to run workflow
   */
  async submitForm(submission: FormSubmission): Promise<FormExecutionResponse> {
    const { data, error } = await apiClient.POST('/forms/{formId}/execute', {
      params: { path: { formId: submission.formId } },
      body: { form_data: submission.formData },
    })
    if (error) throw new Error(`Failed to submit form: ${error}`)
    return data as FormExecutionResponse
  },
}
