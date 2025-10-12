/**
 * Workflow execution types - re-exported from generated API types
 */

import type { components } from './generated/management-api'

// Re-export from generated types
export type WorkflowExecution = components['schemas']['WorkflowExecution'] & {
  logs?: ExecutionLog[]  // Extended with logs from detailed endpoint
}
export type ExecutionStatus = components['schemas']['ExecutionStatus']

// Client-only types (not in backend API)
export interface ExecutionLog {
  timestamp: string
  level: 'debug' | 'info' | 'warning' | 'error'
  message: string
  data?: unknown
}

export interface ExecutionFilters {
  orgId?: string
  workflowName?: string
  status?: ExecutionStatus
  limit?: number
  offset?: number
}
