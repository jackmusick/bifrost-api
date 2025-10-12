/**
 * Workflow type definitions - re-exported from generated API types
 */

import type { components } from './generated/workflow-api'

// Re-export from generated workflow API types
export type WorkflowParameter = components['schemas']['WorkflowParameter']
export type WorkflowMetadata = components['schemas']['WorkflowMetadata']
export type DataProviderMetadata = components['schemas']['DataProviderMetadata']
export type MetadataResponse = components['schemas']['MetadataResponse']
export type WorkflowExecutionRequest = components['schemas']['WorkflowExecutionRequest']
export type WorkflowExecutionResponse = components['schemas']['WorkflowExecutionResponse']
export type DataProviderResponse = components['schemas']['DataProviderResponse']

// Alias for backwards compatibility
export type Workflow = WorkflowMetadata
export type DataProvider = DataProviderMetadata
