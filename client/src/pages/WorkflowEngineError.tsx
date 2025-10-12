import { AlertCircle, RefreshCw, Terminal, BookOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useAuth } from '@/hooks/useAuth'
import { useWorkflowEngineHealth } from '@/hooks/useWorkflowEngineHealth'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'

export function WorkflowEngineError() {
  const navigate = useNavigate()
  const { isPlatformAdmin } = useAuth()
  const { data: engineHealth, refetch, isRefetching } = useWorkflowEngineHealth()

  // If the engine becomes healthy, redirect to workflows page
  useEffect(() => {
    if (engineHealth?.status === 'healthy') {
      navigate('/workflows')
    }
  }, [engineHealth, navigate])

  const handleRetry = async () => {
    await refetch()
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-12rem)]">
      <Card className="max-w-2xl w-full">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-full bg-destructive/10">
              <AlertCircle className="h-8 w-8 text-destructive" />
            </div>
            <div>
              <CardTitle className="text-2xl">Workflow Engine Unavailable</CardTitle>
              <CardDescription>
                Unable to connect to the workflow execution engine
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <Alert>
            <Terminal className="h-4 w-4" />
            <AlertTitle>Service Status</AlertTitle>
            <AlertDescription>
              The workflow engine is currently unavailable. Workflows, forms, and execution
              history cannot be accessed until the service is restored.
            </AlertDescription>
          </Alert>

          {isPlatformAdmin && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Need Help?</CardTitle>
                <CardDescription>
                  View detailed troubleshooting instructions
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  onClick={() => navigate('/docs/troubleshooting/workflow-engine-unavailable')}
                  className="w-full"
                >
                  <BookOpen className="mr-2 h-4 w-4" />
                  View Troubleshooting Documentation
                </Button>
                <p className="text-sm text-muted-foreground mt-3">
                  The documentation includes step-by-step instructions for both development and production environments.
                </p>
              </CardContent>
            </Card>
          )}

          {!isPlatformAdmin && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Contact Administrator</AlertTitle>
              <AlertDescription>
                Please contact your platform administrator to resolve this issue.
                Workflows and forms will be unavailable until the workflow engine is restored.
              </AlertDescription>
            </Alert>
          )}

          <div className="flex gap-3">
            <Button
              onClick={handleRetry}
              disabled={isRefetching}
              className="flex-1"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
              {isRefetching ? 'Checking...' : 'Retry Connection'}
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate('/')}
            >
              Go to Dashboard
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
