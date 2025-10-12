import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, CheckCircle, XCircle, Loader2, Clock, PlayCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import { useExecution } from '@/hooks/useExecutions'
import { useAuth } from '@/hooks/useAuth'
import { PrettyInputDisplay } from '@/components/execution/PrettyInputDisplay'
import type { ExecutionStatus } from '@/types/execution'

export function ExecutionDetails() {
  const { executionId } = useParams()
  const navigate = useNavigate()
  const { isPlatformAdmin } = useAuth()
  const { data: execution, isLoading, error } = useExecution(executionId)

  const getStatusBadge = (status: ExecutionStatus) => {
    switch (status) {
      case 'Success':
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        )
      case 'Failed':
        return (
          <Badge variant="destructive">
            <XCircle className="mr-1 h-3 w-3" />
            Failed
          </Badge>
        )
      case 'Running':
        return (
          <Badge variant="secondary">
            <PlayCircle className="mr-1 h-3 w-3" />
            Running
          </Badge>
        )
      case 'Pending':
        return (
          <Badge variant="outline">
            <Clock className="mr-1 h-3 w-3" />
            Pending
          </Badge>
        )
    }
  }

  const getStatusIcon = (status: ExecutionStatus) => {
    switch (status) {
      case 'Success':
        return <CheckCircle className="h-12 w-12 text-green-500" />
      case 'Failed':
        return <XCircle className="h-12 w-12 text-red-500" />
      case 'Running':
        return <Loader2 className="h-12 w-12 text-blue-500 animate-spin" />
      case 'Pending':
        return <Clock className="h-12 w-12 text-gray-500" />
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

  if (error || !execution) {
    return (
      <div className="space-y-6">
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>
            {error ? 'Failed to load execution details' : 'Execution not found'}
          </AlertDescription>
        </Alert>
        <Button onClick={() => navigate('/history')}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to History
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate('/history')}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight">Execution Details</h1>
          <p className="mt-2 text-muted-foreground">
            Execution ID: <span className="font-mono">{execution.executionId}</span>
          </p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Status</CardTitle>
            <CardDescription>Current execution status</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-6 text-center">
              {getStatusIcon(execution.status)}
              <div className="mt-4">{getStatusBadge(execution.status)}</div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Workflow Information</CardTitle>
            <CardDescription>Details about the workflow</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-sm font-medium text-muted-foreground">Workflow Name</p>
              <p className="font-mono text-sm mt-1">{execution.workflowName}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Executed By</p>
              <p className="text-sm mt-1">{execution.executedBy}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">Started At</p>
              <p className="text-sm mt-1">
                {new Date(execution.startedAt).toLocaleString()}
              </p>
            </div>
            {execution.completedAt && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">Completed At</p>
                <p className="text-sm mt-1">
                  {new Date(execution.completedAt).toLocaleString()}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Input Parameters</CardTitle>
          <CardDescription>Parameters passed to the workflow</CardDescription>
        </CardHeader>
        <CardContent>
          <PrettyInputDisplay
            inputData={execution.inputData}
            showToggle={isPlatformAdmin}
            defaultView={isPlatformAdmin ? 'json' : 'pretty'}
          />
        </CardContent>
      </Card>

      {execution.status === 'Success' && execution.result !== null && (
        <Card>
          <CardHeader>
            <CardTitle>Result</CardTitle>
            <CardDescription>Workflow execution result</CardDescription>
          </CardHeader>
          <CardContent>
            <PrettyInputDisplay
              inputData={execution.result}
              showToggle={isPlatformAdmin}
              defaultView={isPlatformAdmin ? 'json' : 'pretty'}
            />
          </CardContent>
        </Card>
      )}

      {execution.status === 'Failed' && execution.errorMessage && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>Execution Failed</AlertTitle>
          <AlertDescription>
            <pre className="mt-2 text-sm">{execution.errorMessage}</pre>
          </AlertDescription>
        </Alert>
      )}

      {execution.logs && execution.logs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Execution Logs</CardTitle>
            <CardDescription>Workflow execution logs and debug information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {execution.logs.map((log, index) => {
                const levelColor = {
                  debug: 'text-gray-500',
                  info: 'text-blue-600',
                  warning: 'text-yellow-600',
                  error: 'text-red-600'
                }[log.level] || 'text-gray-600'

                return (
                  <div key={index} className="flex gap-3 text-sm font-mono border-b pb-2 last:border-0">
                    <span className="text-muted-foreground whitespace-nowrap">
                      {new Date(log.timestamp).toLocaleTimeString()}
                    </span>
                    <span className={`font-semibold uppercase min-w-[60px] ${levelColor}`}>
                      {log.level}
                    </span>
                    <span className="flex-1">{log.message}</span>
                    {log.data && Object.keys(log.data).length > 0 && (
                      <details className="text-xs">
                        <summary className="cursor-pointer text-muted-foreground">data</summary>
                        <pre className="mt-1 p-2 bg-muted rounded">
                          {JSON.stringify(log.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
