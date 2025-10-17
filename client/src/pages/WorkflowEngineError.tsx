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
import { useNavigate, useLocation } from 'react-router-dom'
import { useEffect } from 'react'

export function WorkflowEngineError() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isPlatformAdmin } = useAuth()
  const { data: serverHealth, refetch, isRefetching } = useWorkflowEngineHealth()

  // If the server becomes healthy, redirect back to where the user was
  useEffect(() => {
    if (serverHealth?.status === 'healthy') {
      // Try to go back to where they were, or fall back to a default page
      const from = (location.state as { from?: string })?.from
      const defaultPath = isPlatformAdmin ? '/workflows' : '/forms'
      navigate(from || defaultPath, { replace: true })
    }
  }, [serverHealth, navigate, location.state, isPlatformAdmin])

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
              <CardTitle className="text-2xl">Server Unavailable</CardTitle>
              <CardDescription>
                Unable to connect to the server
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <Alert>
            <Terminal className="h-4 w-4" />
            <AlertTitle>Service Status</AlertTitle>
            <AlertDescription>
              The server is currently unavailable. Workflows, forms, and execution
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
                  onClick={() => navigate('/docs/troubleshooting/server-unavailable')}
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
                Workflows and forms will be unavailable until the server is restored.
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
