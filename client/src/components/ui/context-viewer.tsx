import { cn } from '@/lib/utils'

export interface ContextViewerProps {
  context: {
    workflow?: Record<string, unknown>
    query?: Record<string, string>
    field?: Record<string, unknown>
  }
  className?: string
  maxHeight?: string
  fieldNames?: string[]
}

/**
 * JSON-formatted context viewer component
 * Displays workflow, query, and field context in a formatted, scrollable view
 */
export function ContextViewer({ context, className, maxHeight = '400px', fieldNames = [] }: ContextViewerProps) {
  const hasWorkflow = context.workflow && Object.keys(context.workflow).length > 0
  const hasQuery = context.query && Object.keys(context.query).length > 0
  const hasField = context.field && Object.keys(context.field).length > 0
  const hasAnyContext = hasWorkflow || hasQuery || hasField

  // Build enhanced context with field names
  const enhancedContext = {
    ...context,
    field: fieldNames.length > 0
      ? fieldNames.reduce((acc, fieldName) => {
          acc[fieldName] = '<value>'
          return acc
        }, {} as Record<string, string>)
      : context.field
  }

  return (
    <div className={cn("space-y-2", className)}>
      <div
        className="bg-slate-950 text-slate-100 rounded-md p-4 font-mono text-xs overflow-auto"
        style={{ maxHeight }}
      >
        {!hasAnyContext && fieldNames.length === 0 ? (
          <div className="text-slate-400 italic">
            No context available yet. Context will be populated when the form loads with a launch workflow or receives query parameters.
          </div>
        ) : (
          <pre className="whitespace-pre-wrap">
            {JSON.stringify(enhancedContext, null, 2)}
          </pre>
        )}
      </div>
      <p className="text-xs text-muted-foreground">
        Available context objects you can use in visibility expressions. Write standard JavaScript: <code className="px-1 py-0.5 bg-muted rounded">&&</code>, <code className="px-1 py-0.5 bg-muted rounded">||</code>, <code className="px-1 py-0.5 bg-muted rounded">===</code>, <code className="px-1 py-0.5 bg-muted rounded">!==</code>, etc.
      </p>
    </div>
  )
}
