import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Clock, AlertCircle, ArrowRight, RefreshCw, Search, Play, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { toast } from 'sonner'
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
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/alert-dialog'
import { formatDate } from '@/lib/utils'
import { apiClient } from '@/lib/api-client'
import { CronTester } from '@/components/schedules/CronTester'
import type { components } from '@/lib/v1'

type ScheduleInfo = components['schemas']['ScheduleInfo']
type SchedulesListResponse = components['schemas']['SchedulesListResponse']

export function Schedules() {
  const navigate = useNavigate()
  const [schedules, setSchedules] = useState<ScheduleInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [triggeringWorkflows, setTriggeringWorkflows] = useState<Set<string>>(new Set())
  const [processingSchedules, setProcessingSchedules] = useState(false)

  const fetchSchedules = async (isRefresh = false) => {
    try {
      if (isRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }
      setError(null)
      const { data, error } = await apiClient.GET('/schedules')
      if (error) {
        throw new Error(JSON.stringify(error))
      }
      setSchedules((data as SchedulesListResponse)?.schedules || [])
    } catch (err) {
      console.error('Failed to fetch schedules:', err)
      setError(
        err instanceof Error ? err.message : 'Failed to load scheduled workflows'
      )
    } finally {
      if (isRefresh) {
        setRefreshing(false)
      } else {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    fetchSchedules()
  }, [])

  const filteredSchedules = schedules.filter((schedule) => {
    const query = searchQuery.toLowerCase()
    return (
      schedule.workflowName.toLowerCase().includes(query) ||
      schedule.workflowDescription.toLowerCase().includes(query) ||
      schedule.cronExpression.toLowerCase().includes(query) ||
      schedule.humanReadable.toLowerCase().includes(query)
    )
  })

  const handleExecutionClick = (executionId: string | null | undefined) => {
    if (executionId) {
      navigate(`/history/${executionId}`)
    }
  }

  const handleTriggerSchedule = async (workflowName: string) => {
    try {
      setTriggeringWorkflows(prev => new Set(prev).add(workflowName))

      const { data, error } = await apiClient.POST('/schedules/{workflow_name}/trigger', {
        params: {
          path: {
            workflow_name: workflowName
          }
        }
      })

      if (error) {
        throw new Error(JSON.stringify(error))
      }

      toast.success('Schedule triggered', {
        description: `${workflowName} has been queued for execution`,
      })

      // Refresh schedules to show updated last run time
      await fetchSchedules(true)

      // Navigate to execution details if we got an execution ID
      if (data?.executionId) {
        navigate(`/history/${data.executionId}`)
      }
    } catch (err) {
      console.error('Failed to trigger schedule:', err)
      toast.error('Failed to trigger schedule', {
        description: err instanceof Error ? err.message : 'An error occurred',
      })
    } finally {
      setTriggeringWorkflows(prev => {
        const next = new Set(prev)
        next.delete(workflowName)
        return next
      })
    }
  }

  const handleProcessSchedules = async () => {
    try {
      setProcessingSchedules(true)

      // Call server-side endpoint that determines which schedules are due
      const { data, error } = await apiClient.POST('/schedules/process')

      if (error) {
        throw new Error(JSON.stringify(error))
      }

      const result = data as { total: number; due: number; executed: number; failed: number }

      if (result.due === 0) {
        toast.info('No schedules due', {
          description: 'All schedules are up to date. The next run will happen automatically.',
        })
      } else if (result.failed === 0) {
        toast.success('Schedules processed', {
          description: `Successfully triggered ${result.executed} schedule${result.executed !== 1 ? 's' : ''}`,
        })
      } else {
        toast.warning('Schedules partially processed', {
          description: `${result.executed} succeeded, ${result.failed} failed`,
        })
      }

      // Refresh schedules to show updated times
      await fetchSchedules(true)
    } catch (err) {
      console.error('Failed to process schedules:', err)
      toast.error('Failed to process schedules', {
        description: err instanceof Error ? err.message : 'An error occurred',
      })
    } finally {
      setProcessingSchedules(false)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-12 bg-gray-100 rounded animate-pulse" />
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  if (schedules.length === 0) {
    return (
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Clock className="h-8 w-8" />
            Scheduled Workflows
          </h1>
          <p className="text-gray-600 mt-2">
            Workflows configured to run automatically on CRON schedules
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              No Scheduled Workflows
            </CardTitle>
            <CardDescription>
              Define workflows with CRON schedules to enable automatic execution
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Workflows with a <code className="bg-gray-100 px-2 py-1 rounded text-sm">schedule</code> parameter will appear here and execute automatically every 5 minutes based on their CRON expression.
              </AlertDescription>
            </Alert>

            <div>
              <h3 className="font-semibold mb-2">Example Workflow</h3>
              <div className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto">
                <pre className="text-sm">{`@workflow(
    name='my_scheduled_workflow',
    description='My Scheduled Workflow',
    schedule='0 9 * * *'  # Every day at 9:00 AM UTC
)
async def my_scheduled_workflow(context):
    return "Scheduled execution completed"`}</pre>
              </div>
            </div>

            <div>
              <h3 className="font-semibold mb-2">Common CRON Patterns</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <code className="text-sm font-mono">*/5 * * * *</code>
                    <p className="text-xs text-gray-600 mt-1">Every 5 minutes</p>
                  </CardContent>
                </Card>
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <code className="text-sm font-mono">0 */6 * * *</code>
                    <p className="text-xs text-gray-600 mt-1">Every 6 hours</p>
                  </CardContent>
                </Card>
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <code className="text-sm font-mono">0 9 * * *</code>
                    <p className="text-xs text-gray-600 mt-1">Daily at 9:00 AM</p>
                  </CardContent>
                </Card>
                <Card className="bg-gray-50">
                  <CardContent className="p-3">
                    <code className="text-sm font-mono">0 0 * * 0</code>
                    <p className="text-xs text-gray-600 mt-1">Weekly on Sunday</p>
                  </CardContent>
                </Card>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
            <Clock className="h-8 w-8" />
            Scheduled Workflows
          </h1>
          <p className="text-gray-600 mt-2">
            Workflows configured to run automatically on CRON schedules
          </p>
        </div>
        <div className="flex items-center gap-0.5">
          {processingSchedules || schedules.length === 0 ? (
            <Button
              variant="outline"
              size="icon"
              className="rounded-r-none"
              disabled
              title={processingSchedules ? 'Processing...' : 'No schedules to process'}
            >
              <Play className="h-4 w-4" />
            </Button>
          ) : (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  className="rounded-r-none"
                  title="Process Due Schedules Now"
                >
                  <Play className="h-4 w-4" />
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Process Due Schedules?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will trigger all workflows that are currently due to run based on their schedule.
                    Workflows are normally processed automatically every 5 minutes.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleProcessSchedules}>
                    Process Now
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
          <Button
            variant="outline"
            size="icon"
            className="rounded-l-none border-l-0"
            onClick={() => fetchSchedules(true)}
            disabled={refreshing}
            title="Refresh schedules"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Schedules are checked every 5 minutes.{' '}
          <Dialog>
            <DialogTrigger asChild>
              <button className="underline hover:text-foreground transition-colors">
                Test CRON expressions
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl">
              <DialogHeader>
                <DialogTitle>CRON Expression Tester</DialogTitle>
                <DialogDescription>
                  Test and validate CRON expressions before using them in workflows
                </DialogDescription>
              </DialogHeader>
              <CronTester />
            </DialogContent>
          </Dialog>
        </AlertDescription>
      </Alert>

      {schedules.length > 0 && (
        <div className="relative max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search schedules..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Active Schedules</CardTitle>
          <CardDescription>
            {filteredSchedules.length} of {schedules.length} workflow{schedules.length !== 1 ? 's' : ''} scheduled
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Workflow</TableHead>
                  <TableHead>Schedule</TableHead>
                  <TableHead>Next Run</TableHead>
                  <TableHead>Last Run</TableHead>
                  <TableHead className="text-right">Executions</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredSchedules.map((schedule) => (
                  <TableRow key={schedule.workflowName}>
                    <TableCell className="font-medium">
                      <div>
                        <p className="font-semibold">{schedule.workflowDescription}</p>
                        <p className="text-xs text-gray-500">{schedule.workflowName}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="space-y-1">
                        <p className="font-mono text-sm">{schedule.cronExpression}</p>
                        {schedule.validationStatus !== 'error' && (
                          <p className="text-xs text-gray-500 dark:text-gray-400">{schedule.humanReadable}</p>
                        )}
                        {schedule.validationStatus === 'warning' && schedule.validationMessage && (
                          <p className="text-xs text-yellow-600 dark:text-yellow-500">
                            Minimum interval: 5 minutes
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      {schedule.validationStatus === 'error' ? (
                        <Badge variant="destructive">
                          Invalid CRON
                        </Badge>
                      ) : schedule.nextRunAt ? (
                        <div className="flex items-center gap-2">
                          <span>{formatDate(schedule.nextRunAt)}</span>
                          {schedule.isOverdue && (
                            <Badge variant="destructive" className="text-xs">
                              Overdue
                            </Badge>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">Not scheduled</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {schedule.lastRunAt ? (
                        <div className="flex items-center gap-2">
                          <span>{formatDate(schedule.lastRunAt)}</span>
                          {schedule.lastExecutionId && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleExecutionClick(schedule.lastExecutionId)}
                              className="h-6 px-2"
                              title="View execution details"
                            >
                              <ArrowRight className="h-3 w-3" />
                            </Button>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-400">Never</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Badge variant="secondary">{schedule.executionCount}</Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-0.5">
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => handleTriggerSchedule(schedule.workflowName)}
                          disabled={triggeringWorkflows.has(schedule.workflowName)}
                          className="h-8 w-8 rounded-r-none"
                          title={triggeringWorkflows.has(schedule.workflowName) ? 'Running...' : 'Run Now'}
                        >
                          <Play className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="outline"
                          size="icon"
                          onClick={() => handleExecutionClick(schedule.lastExecutionId)}
                          disabled={!schedule.lastExecutionId}
                          className="h-8 w-8 rounded-l-none border-l-0"
                          title="View Last Execution"
                        >
                          <Eye className="h-3.5 w-3.5" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          {filteredSchedules.length === 0 && schedules.length > 0 && (
            <div className="text-center py-8 text-gray-500">
              No schedules match your search.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
