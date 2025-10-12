import { useNavigate } from 'react-router-dom'
import {
  Workflow,
  FileText,
  Activity,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  Zap
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useDashboardMetrics } from '@/hooks/useDashboardMetrics'
import { useAuth } from '@/hooks/useAuth'
import { KeyVaultHealthCard } from '@/components/KeyVaultHealthCard'
import { useWorkflowEngineHealth } from '@/hooks/useWorkflowEngineHealth'

export function Dashboard() {
  const navigate = useNavigate()
  const { isPlatformAdmin, isOrgUser } = useAuth()
  const { data: metrics, isLoading, error } = useDashboardMetrics()
  const { data: engineHealth } = useWorkflowEngineHealth()

  // Redirect OrgUsers to /forms (their only accessible page)
  if (isOrgUser && !isPlatformAdmin) {
    navigate('/forms', { replace: true })
    return null
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
            Dashboard
          </h1>
          <p className="leading-7 mt-2 text-muted-foreground">
            Platform overview and metrics
          </p>
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Failed to load dashboard metrics. Please try again later.
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="scroll-m-20 text-4xl font-extrabold tracking-tight lg:text-5xl">
          Dashboard
        </h1>
        <p className="leading-7 mt-2 text-muted-foreground">
          Platform overview and metrics
        </p>
      </div>

      {/* Resource Count Cards - First Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {/* Workflows */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Workflows
            </CardTitle>
            <Workflow className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{metrics?.workflowCount ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Available workflows
            </p>
          </CardContent>
        </Card>

        {/* Forms */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Forms
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">{metrics?.formCount ?? 0}</div>
            )}
            <p className="text-xs text-muted-foreground">
              Active forms
            </p>
          </CardContent>
        </Card>

        {/* Total Executions (30 days) */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Executions (30d)
            </CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">
                {metrics?.executionStats.totalExecutions ?? 0}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Total workflow runs
            </p>
          </CardContent>
        </Card>

        {/* Success Rate */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Success Rate
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-8 w-16" />
            ) : (
              <div className="text-2xl font-bold">
                {metrics?.executionStats.successRate?.toFixed(1) ?? 0}%
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              Last 30 days
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Recent Failures - Compact */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base">Recent Failures</CardTitle>
              <CardDescription className="text-xs">
                Last 30 days
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant={metrics?.executionStats.failedCount === 0 ? "outline" : "destructive"}>
                {isLoading ? '...' : metrics?.executionStats.failedCount ?? 0} Failed
              </Badge>
              <Badge variant="default" className="bg-green-500">
                {isLoading ? '...' : metrics?.executionStats.successCount ?? 0} Success
              </Badge>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-16 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          ) : metrics && metrics.recentFailures.length > 0 ? (
            <div className="space-y-2">
              {metrics.recentFailures.slice(0, 5).map((failure) => (
                <div
                  key={failure.executionId}
                  className="flex items-center justify-between p-2 rounded-md border hover:bg-muted/50 cursor-pointer"
                  onClick={() => navigate(`/history/${failure.executionId}`)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-destructive flex-shrink-0" />
                      <span className="font-mono text-xs font-medium truncate">
                        {failure.workflowName}
                      </span>
                    </div>
                    {failure.errorMessage && (
                      <p className="text-xs text-muted-foreground truncate ml-6">
                        {failure.errorMessage}
                      </p>
                    )}
                  </div>
                  {failure.startedAt && (
                    <span className="text-xs text-muted-foreground ml-2 flex-shrink-0">
                      {new Date(failure.startedAt).toLocaleDateString()}
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center py-4 text-center">
              <CheckCircle2 className="h-8 w-8 text-green-500 mr-2" />
              <p className="text-sm text-muted-foreground">
                All executions successful
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
