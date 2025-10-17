import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { FormRenderer } from '@/components/forms/FormRenderer'
import { useForm } from '@/hooks/useForms'
import { Skeleton } from '@/components/ui/skeleton'
import { useUser } from '@/contexts/UserContext'
import type { components } from '@/lib/v1'

type WorkflowExecutionResponse = components['schemas']['WorkflowExecutionResponse']

export function RunForm() {
  const { formId } = useParams()
  const navigate = useNavigate()
  const { isLoading: userLoading } = useUser()
  const { data: form, isLoading, error } = useForm(formId)
  const [executionResult, setExecutionResult] = useState<WorkflowExecutionResponse | undefined>()

  const handleSuccess = (result: unknown) => {
    setExecutionResult(result as WorkflowExecutionResponse)
  }

  if (isLoading || userLoading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-12 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    )
  }

  if (error || !form) {
    return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {error ? 'Failed to load form' : 'Form not found'}
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/forms')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Forms
        </Button>
      </div>
    )
  }

  if (!form.isActive) {
    return (
      <div className="space-y-6">
        <Alert>
          <AlertTitle>Form Inactive</AlertTitle>
          <AlertDescription>
            This form is currently inactive and cannot be submitted.
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/forms')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Forms
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-center">
        <div className="w-full max-w-2xl">
          <div className="flex items-center gap-4">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => navigate('/forms')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <div>
              <h1 className="text-4xl font-extrabold tracking-tight">{form.name}</h1>
              <p className="mt-2 text-muted-foreground">
                {form.description || `Executes workflow: ${form.linkedWorkflow}`}
              </p>
            </div>
          </div>
        </div>
      </div>

      {executionResult && (
        <div className="flex justify-center">
          <div className="w-full max-w-2xl">
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
                  {executionResult.result && (
                    <div className="mt-3">
                      <div className="font-semibold mb-1">Result:</div>
                      <pre className="bg-muted p-3 rounded-md text-xs overflow-x-auto">
                        {JSON.stringify(executionResult.result, null, 2)}
                      </pre>
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
          </div>
        </div>
      )}

      <FormRenderer form={form} onSuccess={handleSuccess} />
    </div>
  )
}
