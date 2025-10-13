import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, XCircle, Loader2, Clock, RefreshCw, History as HistoryIcon, AlertTriangle, Info, Globe, Building2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useExecutions } from '@/hooks/useExecutions'
import { useScopeStore } from '@/stores/scopeStore'
import { useOrganizations } from '@/hooks/useOrganizations'
import type { ExecutionStatus } from '@/types/execution'

export function ExecutionHistory() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | 'all'>('all')
  const isGlobalScope = useScopeStore((state) => state.isGlobalScope)
  const scope = useScopeStore((state) => state.scope)
  const { data: organizations } = useOrganizations()

  const { data: executions, isFetching, refetch } = useExecutions(
    statusFilter !== 'all' ? { status: statusFilter } : undefined
  )

  // Debug: log when scope changes
  console.log('ExecutionHistory - scope.orgId:', scope.orgId)

  // Helper to get organization name from orgId
  const getOrgName = (orgId?: string) => {
    if (!orgId || orgId === 'GLOBAL') return 'Global'
    const org = organizations?.find(o => o.id === orgId)
    return org?.name || orgId
  }

  const getStatusBadge = (status: ExecutionStatus) => {
    switch (status) {
      case 'Success':
        return (
          <Badge variant="default" className="bg-green-500">
            <CheckCircle className="mr-1 h-3 w-3" />
            Completed
          </Badge>
        )
      case 'CompletedWithErrors':
        return (
          <Badge variant="default" className="bg-yellow-500">
            <AlertTriangle className="mr-1 h-3 w-3" />
            With Errors
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
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
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

  const handleViewDetails = (executionId: string) => {
    navigate(`/history/${executionId}`)
  }

  const filteredExecutions = executions || []

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-6">
      <div className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight">Execution History</h1>
            <p className="mt-2 text-muted-foreground">
              View and track workflow execution history
            </p>
          </div>
        </div>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Executions</CardTitle>
              <CardDescription>
                Recent workflow executions and their status
              </CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col">
          {isGlobalScope && (
            <Alert className="mb-4">
              <Info className="h-4 w-4" />
              <AlertDescription>
                Showing execution logs from the Global partition only. Switch to an organization scope to see that organization's executions.
              </AlertDescription>
            </Alert>
          )}

          <Tabs defaultValue="all" onValueChange={(v) => setStatusFilter(v as ExecutionStatus | 'all')} className="flex flex-col flex-1 overflow-hidden">
            <TabsList className="flex-shrink-0">
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="Success">Completed</TabsTrigger>
              <TabsTrigger value="Running">Running</TabsTrigger>
              <TabsTrigger value="Failed">Failed</TabsTrigger>
              <TabsTrigger value="Pending">Pending</TabsTrigger>
            </TabsList>

            <TabsContent value={statusFilter} className="mt-6 flex-1 overflow-auto">
              {isFetching ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                </div>
              ) : filteredExecutions.length > 0 ? (
                <div className="border rounded-lg overflow-hidden">
                  <div className="overflow-auto max-h-full">
                    <Table>
                      <TableHeader className="sticky top-0 bg-background z-10">
                        <TableRow>
                          {isGlobalScope && <TableHead>Scope</TableHead>}
                          <TableHead>Workflow</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Executed By</TableHead>
                          <TableHead>Started At</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead className="text-right">Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {filteredExecutions.map((execution) => {
                          const duration = execution.completedAt
                            ? Math.round(
                                (new Date(execution.completedAt).getTime() -
                                  new Date(execution.startedAt).getTime()) /
                                  1000
                              )
                            : null

                          const executionOrgId = execution.orgId || 'GLOBAL'
                          const isGlobalExecution = executionOrgId === 'GLOBAL'

                          return (
                            <TableRow key={execution.executionId} className="cursor-pointer hover:bg-muted/50" onClick={() => handleViewDetails(execution.executionId)}>
                              {isGlobalScope && (
                                <TableCell>
                                  <Badge variant={isGlobalExecution ? 'default' : 'outline'} className="text-xs">
                                    {isGlobalExecution ? (
                                      <>
                                        <Globe className="mr-1 h-3 w-3" />
                                        Global
                                      </>
                                    ) : (
                                      <>
                                        <Building2 className="mr-1 h-3 w-3" />
                                        {getOrgName(executionOrgId)}
                                      </>
                                    )}
                                  </Badge>
                                </TableCell>
                              )}
                              <TableCell className="font-mono text-sm">
                                {execution.workflowName}
                              </TableCell>
                              <TableCell>{getStatusBadge(execution.status)}</TableCell>
                              <TableCell>{execution.executedBy}</TableCell>
                              <TableCell className="text-sm">
                                {new Date(execution.startedAt).toLocaleString()}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {duration !== null ? `${duration}s` : '-'}
                              </TableCell>
                              <TableCell className="text-right">
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleViewDetails(execution.executionId)
                                  }}
                                >
                                  View Details
                                </Button>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <HistoryIcon className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">No executions found</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Execute a workflow to see it appear here
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  )
}
