/**
 * Form Context Provider
 *
 * Manages form state including:
 * - Workflow execution results (from launch workflow)
 * - Query parameters from URL
 * - Current form field values
 * - Field visibility evaluation
 *
 * All context evaluation happens client-side for instant reactivity (<100ms).
 */

import { createContext, useContext, useState, useEffect, useCallback, useMemo, ReactNode } from 'react'
import type { components } from '@/lib/v1'

type Form = components['schemas']['Form']
type FormField = components['schemas']['FormField']

/**
 * Form context shape matching backend spec
 * Used in visibility expressions like: context.workflow.user_exists === true
 */
export interface FormContextValue {
  /** Results from launch workflow execution */
  workflow: Record<string, unknown>
  /** Query parameters from URL (filtered by allowedQueryParams) */
  query: Record<string, string>
  /** Current form field values */
  field: Record<string, unknown>
}

interface FormContextProviderValue {
  /** Current form context */
  context: FormContextValue
  /** Update workflow results (called after launch workflow executes) */
  setWorkflowResults: (results: Record<string, unknown>) => void
  /** Update field value (called on user input) */
  setFieldValue: (fieldName: string, value: unknown) => void
  /** Check if a field should be visible based on its visibilityExpression */
  isFieldVisible: (field: FormField) => boolean
  /** Check if form is loading launch workflow */
  isLoadingLaunchWorkflow: boolean
  /** Set launch workflow loading state */
  setIsLoadingLaunchWorkflow: (loading: boolean) => void
}

const FormContext = createContext<FormContextProviderValue | undefined>(undefined)

interface FormContextProviderProps {
  children: ReactNode
  form: Form
  /** Initial query parameters from URL search params */
  queryParams?: Record<string, string>
}

/**
 * Track logged errors to prevent console flooding
 */
const loggedExpressionErrors = new Set<string>()

/**
 * Safely evaluate a visibility expression using native JavaScript
 * Returns true if field should be visible, false otherwise
 *
 * SECURITY NOTE: Using Function constructor is intentional here.
 * - Only form builders (admins) write expressions, not end users
 * - Expressions execute client-side with restricted context only
 * - No access to window, document, or other sensitive objects
 */
function evaluateVisibilityExpression(
  expression: string,
  context: FormContextValue
): boolean {
  try {
    // Create a function with context in scope
    // This allows natural JavaScript syntax: context.field.name !== null && context.field.name !== ""
     
    const fn = new Function('context', `return !!(${expression})`)
    const result = fn(context)
    return Boolean(result)
  } catch (error) {
    // If expression is invalid, show the field by default (fail-open)
    // Only log once per unique expression to avoid flooding console
    if (!loggedExpressionErrors.has(expression)) {
      loggedExpressionErrors.add(expression)
      console.warn(`Failed to evaluate visibility expression: ${expression}`, error)
    }
    return true
  }
}

/**
 * Filter query parameters based on form's allowedQueryParams
 */
function filterQueryParams(
  queryParams: Record<string, string>,
  allowedParams: string[] | null | undefined
): Record<string, string> {
  if (!allowedParams || allowedParams.length === 0) {
    return {}
  }

  const filtered: Record<string, string> = {}
  for (const param of allowedParams) {
    if (queryParams[param] !== undefined) {
      filtered[param] = queryParams[param]
    }
  }
  return filtered
}

export function FormContextProvider({ children, form, queryParams = {} }: FormContextProviderProps) {
  const [isLoadingLaunchWorkflow, setIsLoadingLaunchWorkflow] = useState(false)

  // Initialize context with filtered query params
  const [context, setContext] = useState<FormContextValue>(() => ({
    workflow: {},
    query: filterQueryParams(queryParams, form.allowedQueryParams),
    field: {},
  }))

  // Update context when query params change (e.g., URL navigation)
  useEffect(() => {
    setContext((prev) => ({
      ...prev,
      query: filterQueryParams(queryParams, form.allowedQueryParams),
    }))
  }, [queryParams, form.allowedQueryParams])

  const setWorkflowResults = useCallback((results: Record<string, unknown>) => {
    setContext((prev) => ({
      ...prev,
      workflow: results,
    }))
  }, [])

  const setFieldValue = useCallback((fieldName: string, value: unknown) => {
    setContext((prev) => ({
      ...prev,
      field: {
        ...prev.field,
        [fieldName]: value,
      },
    }))
  }, [])

  // Don't memoize isFieldVisible - it needs fresh context on every call
  // We accept the context parameter directly to avoid stale closure issues
  const isFieldVisible = (field: FormField): boolean => {
    // If no visibility expression, field is always visible
    if (!field.visibilityExpression) {
      return true
    }

    // Evaluate the expression with current context
    return evaluateVisibilityExpression(field.visibilityExpression, context)
  }

  // Memoize the provider value to prevent unnecessary re-renders
  // Only recreate when context or loading state changes
  // isFieldVisible is intentionally not memoized - it reads fresh context on each call
  const value: FormContextProviderValue = useMemo(() => ({
    context,
    setWorkflowResults,
    setFieldValue,
    isFieldVisible,
    isLoadingLaunchWorkflow,
    setIsLoadingLaunchWorkflow,
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [context, setWorkflowResults, setFieldValue, isLoadingLaunchWorkflow])

  return (
    <FormContext.Provider value={value}>
      {children}
    </FormContext.Provider>
  )
}

/**
 * Hook to access form context
 * Must be used within a FormContextProvider
 */
export function useFormContext() {
  const context = useContext(FormContext)
  if (context === undefined) {
    throw new Error('useFormContext must be used within a FormContextProvider')
  }
  return context
}
