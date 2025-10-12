import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { useWorkflowsMetadata, useExecuteWorkflow } from '@/hooks/useWorkflows'
import { useUser } from '@/contexts/UserContext'
import { PrettyInputDisplay } from '@/components/execution/PrettyInputDisplay'
import type { WorkflowParameter } from '@/types/workflow'

export function ExecuteWorkflow() {
  const { workflowName } = useParams()
  const navigate = useNavigate()
  const { orgId } = useUser()
  const { data, isLoading } = useWorkflowsMetadata()
  const executeWorkflow = useExecuteWorkflow()

  const [parameters, setParameters] = useState<Record<string, any>>({})
  const [executionResult, setExecutionResult] = useState<any | undefined>()

  const workflow = data?.workflows?.find((w) => w.name === workflowName)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!workflow) return

    const request: any = {
      workflowName: workflow.name ?? '',
      parameters,
    }

    if (orgId) {
      request.orgId = orgId
    }

    const result = await executeWorkflow.mutateAsync(request)
    setExecutionResult(result)
  }

  const handleParameterChange = (paramName: string, value: any) => {
    setParameters((prev) => ({
      ...prev,
      [paramName]: value,
    }))
  }

  const renderParameterInput = (param: WorkflowParameter) => {
    const value = parameters[param.name ?? ''] ?? param.defaultValue ?? ''

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
              {param.label ?? ''}
              {param.helpText && (
                <span className="block text-xs text-muted-foreground mt-1">
                  {param.helpText}
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
              {param.label ?? ''}
              {param.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={param.name ?? 'number'}
              type="number"
              step={param.type === 'float' ? 'any' : '1'}
              value={value}
              onChange={(e) =>
                handleParameterChange(
                  param.name ?? '',
                  param.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value)
                )
              }
              required={param.required}
            />
            {param.helpText && (
              <p className="text-xs text-muted-foreground">{param.helpText}</p>
            )}
          </div>
        )

      case 'list':
        return (
          <div className="space-y-2">
            <Label htmlFor={param.name ?? 'list'}>
              {param.label ?? ''}
              {param.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={param.name ?? 'list'}
              type="text"
              value={Array.isArray(value) ? value.join(', ') : value}
              onChange={(e) =>
                handleParameterChange(
                  param.name ?? '',
                  e.target.value.split(',').map((v) => v.trim())
                )
              }
              placeholder="Comma-separated values"
              required={param.required}
            />
            {param.helpText && (
              <p className="text-xs text-muted-foreground">{param.helpText}</p>
            )}
          </div>
        )

      default:
        // string, email, json
        return (
          <div className="space-y-2">
            <Label htmlFor={param.name ?? 'text'}>
              {param.label ?? ''}
              {param.required && <span className="text-destructive">*</span>}
            </Label>
            <Input
              id={param.name ?? 'text'}
              type={param.type === 'email' ? 'email' : 'text'}
              value={value}
              onChange={(e) => handleParameterChange(param.name ?? '', e.target.value)}
              required={param.required}
            />
            {param.helpText && (
              <p className="text-xs text-muted-foreground">{param.helpText}</p>
            )}
          </div>
        )
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (!workflow) {
    return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>Workflow not found</AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/workflows')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Workflows
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => navigate('/workflows')}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight">Execute Workflow</h1>
          <p className="mt-2 text-muted-foreground">
            Workflow: <span className="font-mono">{workflow.name}</span>
          </p>
        </div>
      </div>

      {executionResult && (
        <>
          <Alert variant={executionResult.status === 'Success' ? 'default' : 'destructive'}>
            {executionResult.status === 'Success' ? (
              <CheckCircle className="h-4 w-4 text-green-500" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <AlertTitle>
              {executionResult.status === 'Success' ? 'Workflow Completed Successfully' : 'Workflow Execution Failed'}
            </AlertTitle>
            <AlertDescription>
              <div className="space-y-2">
                <div>
                  Execution ID: <span className="font-mono text-xs">{executionResult.executionId}</span>
                </div>
                {executionResult.durationMs && (
                  <div>
                    Duration: <span className="font-mono text-xs">{executionResult.durationMs}ms</span>
                  </div>
                )}
                {executionResult.error && (
                  <div className="mt-3">
                    <div className="font-semibold mb-1">Error:</div>
                    <div className="text-sm text-destructive">{executionResult.error}</div>
                  </div>
                )}
                <Button
                  variant="link"
                  className="px-0 mt-2"
                  onClick={() => navigate(`/history/${executionResult.executionId}`)}
                >
                  View execution details
                </Button>
              </div>
            </AlertDescription>
          </Alert>

          {executionResult.result && (
            <Card>
              <CardHeader>
                <CardTitle>Result</CardTitle>
                <CardDescription>Workflow execution result</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="max-h-[600px] overflow-y-auto">
                  <PrettyInputDisplay
                    inputData={executionResult.result}
                    showToggle={true}
                    defaultView="json"
                  />
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{workflow.name}</CardTitle>
          {workflow.description && (
            <CardDescription>{workflow.description}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {workflow.parameters?.map((param) => (
              <div key={param.name ?? 'param'}>{renderParameterInput(param)}</div>
            ))}

            <Button
              type="submit"
              className="w-full"
              disabled={executeWorkflow.isPending}
            >
              <Play className="mr-2 h-4 w-4" />
              {executeWorkflow.isPending ? 'Executing...' : 'Execute Workflow'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
