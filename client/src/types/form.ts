/**
 * Form types - re-exported from generated API types
 */

import type { components } from './generated/management-api'

// Re-export types from generated API
export type Form = components['schemas']['Form']
export type FormSchema = components['schemas']['FormSchema']
export type FormField = components['schemas']['FormField']
export type FormFieldType = components['schemas']['FormFieldType']
export type CreateFormRequest = components['schemas']['CreateFormRequest']
export type UpdateFormRequest = components['schemas']['UpdateFormRequest']
export type WorkflowExecution = components['schemas']['WorkflowExecution']
export type ExecutionStatus = components['schemas']['ExecutionStatus']

// Additional client-only types
export interface FormSubmission {
  formId: string
  formData: Record<string, unknown>
}

export interface FormExecutionResponse {
  executionId: string
  status: ExecutionStatus
  workflowName: string
  result?: unknown
  error?: string
  createdAt: string
}
