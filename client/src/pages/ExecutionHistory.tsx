import React, { useState, useMemo, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle, XCircle, Loader2, Clock, RefreshCw, History as HistoryIcon, Globe, Building2, Eraser, AlertCircle, Info, Eye } from 'lucide-react'
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
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import { useExecutions } from '@/hooks/useExecutions'
import { useScopeStore } from '@/stores/scopeStore'
import { formatDate } from '@/lib/utils'
import { SearchBox } from '@/components/search/SearchBox'
import { useSearch } from '@/hooks/useSearch'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from '@/components/ui/pagination'
// import { useOrganizations } from '@/hooks/useOrganizations'
import type { components } from '@/lib/v1'
type ExecutionStatus = components['schemas']['ExecutionStatus']

interface StuckExecution {
  executionId: string
  workflowName: string
  status: string
  executedBy: string
  executedByName: string
  startedAt: string | null
}

export function ExecutionHistory() {
  const navigate = useNavigate()
  const [statusFilter, setStatusFilter] = useState<ExecutionStatus | 'all'>('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [cleanupDialogOpen, setCleanupDialogOpen] = useState(false)
  const [stuckExecutions, setStuckExecutions] = useState<StuckExecution[]>([])
  const [loadingStuck, setLoadingStuck] = useState(false)
  const [cleaningUp, setCleaningUp] = useState(false)
  const isGlobalScope = useScopeStore((state) => state.isGlobalScope)
  const scope = useScopeStore((state) => state.scope)
  // Pagination state - stack of continuation tokens for "back" navigation
  const [pageStack, setPageStack] = useState<(string | null)[]>([])
  const [currentToken, setCurrentToken] = useState<string | undefined>(undefined)
  // const { data: organization } = useOrganizations()
  // const organizations = organization ? [organization] : []

  const { data: response, isFetching, refetch } = useExecutions(
    statusFilter !== 'all' ? { status: statusFilter } : undefined,
    currentToken
  )

  const executions = response?.executions || []
  const hasMore = response?.hasMore || false
  const nextToken = response?.continuationToken || null

  // Debug: log when scope changes
  console.log('ExecutionHistory - scope.orgId:', scope.orgId)

  // Find executions that are still running (for display purposes)
  const runningExecutionIds = useMemo(() => {
    if (!executions) return []
    return executions
      .filter((exec) => exec.status === 'Pending' || exec.status === 'Running')
      .map((exec) => exec.executionId)
  }, [executions])

  // Polling disabled - users can manually refresh to see status updates
  const isPolling = false

  // Helper to get organization name from orgId (currently unused since orgId not available in Execution schema)
  // const getOrgName = (orgId?: string) => {
  //   if (!orgId || orgId === 'GLOBAL') return 'Global'
  //   const org = organizations?.find(o => o.id === orgId)
  //   return org?.name || orgId
  // }

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
      case 'Timeout':
        return (
          <Badge variant="destructive">
            <XCircle className="mr-1 h-3 w-3" />
            Timeout
          </Badge>
        )
      case 'CompletedWithErrors':
        return (
          <Badge variant="outline" className="border-yellow-500 text-yellow-600 dark:text-yellow-500">
            <AlertCircle className="mr-1 h-3 w-3" />
            Completed with Errors
          </Badge>
        )
      default:
        return (
          <Badge variant="outline">
            Unknown
          </Badge>
        )
    }
  }

  const handleViewDetails = (executionId: string) => {
    navigate(`/history/${executionId}`)
  }

  const handleOpenCleanup = async () => {
    setCleanupDialogOpen(true)
    setLoadingStuck(true)

    try {
      const response = await apiClient.GET('/executions/cleanup/stuck')
      if (response.data) {
        setStuckExecutions(response.data.executions || [])
      }
    } catch (error) {
      console.error('Failed to fetch stuck executions:', error)
      toast.error('Failed to load stuck executions')
    } finally {
      setLoadingStuck(false)
    }
  }

  const handleTriggerCleanup = async () => {
    setCleaningUp(true)

    try {
      const response = await apiClient.POST('/executions/cleanup/trigger', {})
      if (response.data) {
        toast.success(`Cleaned up ${response.data.cleaned} stuck executions`)
        setCleanupDialogOpen(false)
        // Refetch executions to show updated status
        refetch()
      }
    } catch (error) {
      console.error('Failed to trigger cleanup:', error)
      toast.error('Failed to trigger cleanup')
    } finally {
      setCleaningUp(false)
    }
  }

  // Apply search filter
  const searchFilteredExecutions = useSearch(
    executions || [],
    searchTerm,
    [
      'workflowName',
      'executedByName',
      'executionId',
      (exec) => exec.status
    ]
  )

  const filteredExecutions = searchFilteredExecutions

  // Pagination handlers
  const handleNextPage = () => {
    if (nextToken) {
      // Push current state to stack for "back" navigation
      setPageStack([...pageStack, currentToken || null])
      setCurrentToken(nextToken)
    }
  }

  const handlePreviousPage = () => {
    if (pageStack.length > 0) {
      // Pop from stack to go back
      const newStack = [...pageStack]
      const previousToken = newStack.pop()
      setPageStack(newStack)
      setCurrentToken(previousToken || undefined)
    }
  }

  // Reset pagination when filters change
  useEffect(() => {
    setPageStack([])
    setCurrentToken(undefined)
  }, [statusFilter])

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
                {isPolling && (
                  <span className="ml-2 inline-flex items-center text-blue-600">
                    <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                    Auto-refreshing {runningExecutionIds.length} running execution{runningExecutionIds.length !== 1 ? 's' : ''}
                  </span>
                )}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Dialog open={cleanupDialogOpen} onOpenChange={setCleanupDialogOpen}>
                <DialogTrigger asChild>
                  <Button variant="outline" size="icon" onClick={handleOpenCleanup} title="Cleanup Stuck Executions">
                    <Eraser className="h-4 w-4" />
                  </Button>
                </DialogTrigger>
                <DialogContent className="max-w-3xl">
                  <DialogHeader>
                    <DialogTitle>Cleanup Stuck Executions</DialogTitle>
                    <DialogDescription>
                      Stuck executions are workflows that have been in Pending status for 10+ minutes or Running status for 30+ minutes.
                    </DialogDescription>
                  </DialogHeader>

                  {loadingStuck ? (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                    </div>
                  ) : stuckExecutions.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-center">
                      <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                      <h3 className="text-lg font-semibold">No Stuck Executions</h3>
                      <p className="mt-2 text-sm text-muted-foreground">
                        All executions are running normally
                      </p>
                    </div>
                  ) : (
                    <div className="border rounded-lg">
                      <Table>
                        <TableHeader>
                          <TableRow>
                            <TableHead>Workflow</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Executed By</TableHead>
                            <TableHead>Started At</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {stuckExecutions.map((execution) => (
                            <TableRow key={execution.executionId}>
                              <TableCell className="font-mono text-sm">{execution.workflowName}</TableCell>
                              <TableCell>
                                <Badge variant={execution.status === 'Pending' ? 'outline' : 'secondary'}>
                                  {execution.status}
                                </Badge>
                              </TableCell>
                              <TableCell>{execution.executedByName}</TableCell>
                              <TableCell className="text-sm">
                                {execution.startedAt ? formatDate(execution.startedAt) : '-'}
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </div>
                  )}

                  <DialogFooter>
                    <Button variant="outline" onClick={() => setCleanupDialogOpen(false)}>
                      Cancel
                    </Button>
                    <Button
                      onClick={handleTriggerCleanup}
                      disabled={stuckExecutions.length === 0 || cleaningUp}
                    >
                      {cleaningUp && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                      Cleanup {stuckExecutions.length} Execution{stuckExecutions.length !== 1 ? 's' : ''}
                    </Button>
                  </DialogFooter>
                </DialogContent>
              </Dialog>

              <Button variant="outline" size="icon" onClick={() => refetch()} disabled={isFetching}>
                <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col">
          <Tabs defaultValue="all" onValueChange={(v) => setStatusFilter(v as ExecutionStatus | 'all')} className="flex flex-col flex-1 overflow-hidden">
            <div className="flex-shrink-0 flex items-center justify-between gap-4 mb-4">
              {/* Search Box */}
              <SearchBox
                value={searchTerm}
                onChange={setSearchTerm}
                placeholder="Search by workflow name, user, or execution ID..."
                className="flex-1 max-w-2xl"
              />

              {/* Filter Tabs */}
              <TabsList>
                <TabsTrigger value="all">All</TabsTrigger>
                <TabsTrigger value="Success">Completed</TabsTrigger>
                <TabsTrigger value="Running">Running</TabsTrigger>
                <TabsTrigger value="Failed">Failed</TabsTrigger>
                <TabsTrigger value="Pending">Pending</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value={statusFilter} className="mt-0 flex-1 overflow-auto">
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
                          <TableHead>Completed At</TableHead>
                          <TableHead>Duration</TableHead>
                          <TableHead className="text-right"></TableHead>
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

                          // For now, treat all executions as global since orgId is not available in Execution schema
                          const isGlobalExecution = true

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
                                        Global
                                      </>
                                    )}
                                  </Badge>
                                </TableCell>
                              )}
                              <TableCell className="font-mono text-sm">
                                {execution.workflowName}
                              </TableCell>
                              <TableCell>
                                <div className="flex items-center gap-2">
                                  {getStatusBadge(execution.status)}
                                  {execution.errorMessage && (
                                    <TooltipProvider>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Info className="h-4 w-4 text-destructive cursor-help" />
                                        </TooltipTrigger>
                                        <TooltipContent side="right" className="max-w-md bg-popover text-popover-foreground">
                                          <p className="text-sm">{execution.errorMessage}</p>
                                        </TooltipContent>
                                      </Tooltip>
                                    </TooltipProvider>
                                  )}
                                </div>
                              </TableCell>
                              <TableCell>{execution.executedByName}</TableCell>
                              <TableCell className="text-sm">
                                {formatDate(execution.startedAt)}
                              </TableCell>
                              <TableCell className="text-sm">
                                {execution.completedAt ? formatDate(execution.completedAt) : '-'}
                              </TableCell>
                              <TableCell className="text-sm text-muted-foreground">
                                {duration !== null ? `${duration}s` : '-'}
                              </TableCell>
                              <TableCell className="text-right">
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    handleViewDetails(execution.executionId)
                                  }}
                                  title="View Details"
                                >
                                  <Eye className="h-4 w-4" />
                                </Button>
                              </TableCell>
                            </TableRow>
                          )
                        })}
                      </TableBody>
                    </Table>
                  </div>

                  {/* Pagination */}
                  {filteredExecutions.length > 0 && (
                    <div className="px-6 py-4 border-t flex items-center justify-center">
                      <Pagination>
                        <PaginationContent>
                          <PaginationItem>
                            <PaginationPrevious
                              onClick={(e) => {
                                e.preventDefault()
                                handlePreviousPage()
                              }}
                              className={
                                pageStack.length === 0 || isFetching
                                  ? "pointer-events-none opacity-50"
                                  : "cursor-pointer"
                              }
                              aria-disabled={pageStack.length === 0 || isFetching}
                            />
                          </PaginationItem>
                          <PaginationItem>
                            <PaginationLink isActive>
                              {pageStack.length + 1}
                            </PaginationLink>
                          </PaginationItem>
                          <PaginationItem>
                            <PaginationNext
                              onClick={(e) => {
                                e.preventDefault()
                                handleNextPage()
                              }}
                              className={
                                !hasMore || isFetching
                                  ? "pointer-events-none opacity-50"
                                  : "cursor-pointer"
                              }
                              aria-disabled={!hasMore || isFetching}
                            />
                          </PaginationItem>
                        </PaginationContent>
                      </Pagination>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <HistoryIcon className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">
                    {searchTerm ? 'No executions match your search' : 'No executions found'}
                  </h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    {searchTerm
                      ? 'Try adjusting your search term or clear the filter'
                      : 'Execute a workflow to see it appear here'
                    }
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
