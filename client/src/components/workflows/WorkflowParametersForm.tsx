import { useState } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Button } from '@/components/ui/button'
import { Play } from 'lucide-react'
import type { components } from '@/lib/v1'
type WorkflowParameter = components['schemas']['WorkflowParameter']

interface WorkflowParametersFormProps {
  parameters: WorkflowParameter[]
  onExecute: (params: Record<string, unknown>) => void | Promise<void>
  isExecuting?: boolean
  showExecuteButton?: boolean
  executeButtonText?: string
  className?: string
}

/**
 * Reusable form for entering workflow parameters
 * Used in both ExecuteWorkflow page and FormBuilder test launch workflow dialog
 */
export function WorkflowParametersForm({
  parameters,
  onExecute,
  isExecuting = false,
  showExecuteButton = true,
  executeButtonText = 'Execute Workflow',
  className,
}: WorkflowParametersFormProps) {
  const [paramValues, setParamValues] = useState<Record<string, unknown>>({})

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onExecute(paramValues)
  }

  const handleParameterChange = (paramName: string, value: unknown) => {
    setParamValues((prev) => ({
      ...prev,
      [paramName]: value,
    }))
  }

  const renderParameterInput = (param: WorkflowParameter) => {
    const value = paramValues[param.name ?? '']

    switch (param.type) {
      case 'bool':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={param.name ?? 'checkbox'}
              checked={!!value}
              onCheckedChange={(checked) => handleParameterChange(param.name ?? '', checked)}
            />
            <Label htmlFor={param.name ?? 'checkbox'} className="text-sm font-normal">
              {param.name}
              {param.description && (
                <span className="block text-xs text-muted-foreground mt-1">
                  {param.description}
                </span>
              )}
            </Label>
          </div>
        )

      case 'int':
      case 'float':
        return (
          <div className="space-y-2">
            <Label htmlFor={param.name ?? 'number'}>
              {param.name}
              {param.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={param.name ?? 'number'}
              type="number"
              step={param.type === 'float' ? '0.1' : '1'}
              value={value as string | number | undefined ?? ''}
              onChange={(e) =>
                handleParameterChange(
                  param.name ?? '',
                  param.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value)
                )
              }
              required={param.required}
            />
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
          </div>
        )

      case 'list':
        return (
          <div className="space-y-2">
            <Label htmlFor={param.name ?? 'list'}>
              {param.name ?? ''}
              {param.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={param.name ?? 'list'}
              type="text"
              value={Array.isArray(value) ? value.join(', ') : (value as string ?? '')}
              onChange={(e) =>
                handleParameterChange(
                  param.name ?? '',
                  e.target.value.split(',').map((v) => v.trim())
                )
              }
              placeholder="Comma-separated values"
              required={param.required}
            />
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
          </div>
        )

      default:
        // string, email, json
        return (
          <div className="space-y-2">
            <Label htmlFor={param.name ?? 'text'}>
              {param.name ?? ''}
              {param.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={param.name ?? 'text'}
              type={param.type === 'email' ? 'email' : 'text'}
              value={(value as string) ?? ''}
              onChange={(e) => handleParameterChange(param.name ?? '', e.target.value)}
              required={param.required}
            />
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
          </div>
        )
    }
  }

  if (parameters.length === 0) {
    return (
      <div className={className}>
        <p className="text-sm text-muted-foreground">This workflow has no parameters.</p>
        {showExecuteButton && (
          <Button
            type="button"
            className="w-full mt-4"
            disabled={isExecuting}
            onClick={() => onExecute({})}
          >
            <Play className="mr-2 h-4 w-4" />
            {isExecuting ? 'Executing...' : executeButtonText}
          </Button>
        )}
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className={className}>
      <div className="space-y-4">
        {parameters.map((param) => (
          <div key={param.name ?? 'param'}>{renderParameterInput(param)}</div>
        ))}
      </div>

      {showExecuteButton && (
        <Button
          type="submit"
          className="w-full mt-6"
          disabled={isExecuting}
        >
          <Play className="mr-2 h-4 w-4" />
          {isExecuting ? 'Executing...' : executeButtonText}
        </Button>
      )}
    </form>
  )
}
