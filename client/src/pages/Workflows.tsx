import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlayCircle, Code, RefreshCw, Webhook, AlertTriangle, LayoutGrid, Table as TableIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useWorkflowsMetadata } from '@/hooks/useWorkflows'
import { useWorkflowKeys } from '@/hooks/useWorkflowKeys'
import { HttpTriggerDialog } from '@/components/workflows/HttpTriggerDialog'
import { SearchBox } from '@/components/search/SearchBox'
import { useSearch } from '@/hooks/useSearch'
import type { components } from '@/lib/v1'
type Workflow = components['schemas']['WorkflowMetadata']

export function Workflows() {
  const navigate = useNavigate()
  const { data, isLoading, refetch } = useWorkflowsMetadata()
  const { data: apiKeys } = useWorkflowKeys({ includeRevoked: false })
  const [webhookDialogOpen, setWebhookDialogOpen] = useState(false)
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')

  const workflows = data?.workflows || []

  // Apply search filter
  const filteredWorkflows = useSearch(
    workflows,
    searchTerm,
    [
      'name',
      'description',
      'category',
      (w) => w.parameters?.map(p => p.name).join(' ') || ''
    ]
  )

  // Create a map of workflows that have API keys
  const workflowsWithKeys = useMemo(() => {
    if (!apiKeys) return new Set<string>()

    const workflowSet = new Set<string>()
    apiKeys.forEach((key) => {
      if (key.workflowId && !key.revokedAt) {
        workflowSet.add(key.workflowId)
      }
    })
    return workflowSet
  }, [apiKeys])

  const hasGlobalKey = useMemo(() => {
    if (!apiKeys) return false
    return apiKeys.some((key) => !key.workflowId && !key.revokedAt)
  }, [apiKeys])

  const handleExecute = (workflowName: string) => {
    navigate(`/workflows/${workflowName}/execute`)
  }

  const handleShowWebhook = (workflow: Workflow) => {
    setSelectedWorkflow(workflow)
    setWebhookDialogOpen(true)
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight">Workflows</h1>
          <p className="mt-2 text-muted-foreground">
            Execute workflows directly with custom parameters
          </p>
        </div>
        <div className="flex gap-2">
          <ToggleGroup type="single" value={viewMode} onValueChange={(value: string) => value && setViewMode(value as 'grid' | 'table')}>
            <ToggleGroupItem value="grid" aria-label="Grid view" size="sm">
              <LayoutGrid className="h-4 w-4" />
            </ToggleGroupItem>
            <ToggleGroupItem value="table" aria-label="Table view" size="sm">
              <TableIcon className="h-4 w-4" />
            </ToggleGroupItem>
          </ToggleGroup>
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Search Box */}
      <SearchBox
        value={searchTerm}
        onChange={setSearchTerm}
        placeholder="Search workflows by name, description, or category..."
        className="max-w-md"
      />

      {isLoading ? (
        viewMode === 'grid' ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <Skeleton key={i} className="h-48 w-full" />
            ))}
          </div>
        ) : (
          <div className="space-y-2">
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        )
      ) : filteredWorkflows.length > 0 ? (
        viewMode === 'grid' ? (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredWorkflows.map((workflow) => (
              <Card key={workflow.name} className="hover:border-primary transition-colors flex flex-col">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span className="font-mono text-base">{workflow.name}</span>
                    <div className="flex items-center gap-1">
                      {workflow.endpointEnabled && (
                        <Badge
                          variant={
                            workflow.publicEndpoint
                              ? "destructive"
                              : (hasGlobalKey || workflowsWithKeys.has(workflow.name ?? '') ? "default" : "outline")
                          }
                          className={`cursor-pointer transition-colors ${
                            workflow.publicEndpoint
                              ? 'bg-orange-600 hover:bg-orange-700 border-orange-600'
                              : hasGlobalKey || workflowsWithKeys.has(workflow.name ?? '')
                              ? 'bg-green-600 hover:bg-green-700'
                              : 'text-muted-foreground hover:bg-accent'
                          }`}
                          onClick={(e) => {
                            e.stopPropagation()
                            handleShowWebhook(workflow)
                          }}
                          title={
                            workflow.publicEndpoint
                              ? 'Public webhook endpoint - no authentication required'
                              : (hasGlobalKey || workflowsWithKeys.has(workflow.name ?? '')
                                ? 'HTTP endpoint enabled with API key'
                                : 'HTTP endpoint (no API key configured)')
                          }
                        >
                          {workflow.publicEndpoint ? (
                            <AlertTriangle className="mr-1 h-3 w-3" />
                          ) : (
                            <Webhook className="mr-1 h-3 w-3" />
                          )}
                          Endpoint
                        </Badge>
                      )}
                      {workflow.disableGlobalKey && (
                        <Badge
                          variant="outline"
                          className="bg-orange-600 text-white hover:bg-orange-700 border-orange-600"
                          title="This workflow only accepts workflow-specific API keys (global keys are disabled)"
                        >
                          Global Opt-Out
                        </Badge>
                      )}
                      {workflow.category && (
                        <Badge variant="secondary">{workflow.category}</Badge>
                      )}
                    </div>
                  </CardTitle>
                  {workflow.description && (
                    <CardDescription>{workflow.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent className="space-y-4 flex-1 flex flex-col">
                  <div className="flex-1 space-y-4">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Parameters</p>
                      <p className="text-sm mt-1">
                        {workflow.parameters?.length ?? 0} parameter
                        {workflow.parameters?.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                  </div>
                  <Button
                    className="w-full mt-auto"
                    onClick={() => handleExecute(workflow.name ?? '')}
                  >
                    <PlayCircle className="mr-2 h-4 w-4" />
                    Execute Workflow
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Parameters</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredWorkflows.map((workflow) => (
                  <TableRow key={workflow.name}>
                    <TableCell className="font-mono font-medium">{workflow.name}</TableCell>
                    <TableCell className="max-w-xs truncate text-muted-foreground">
                      {workflow.description || <span className="italic">No description</span>}
                    </TableCell>
                    <TableCell className="text-right">{workflow.parameters?.length ?? 0}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1">
                        {workflow.endpointEnabled && (
                          <Badge
                            variant={
                              workflow.publicEndpoint
                                ? "destructive"
                                : (hasGlobalKey || workflowsWithKeys.has(workflow.name ?? '') ? "default" : "outline")
                            }
                            className={`cursor-pointer transition-colors text-xs ${
                              workflow.publicEndpoint
                                ? 'bg-orange-600 hover:bg-orange-700 border-orange-600'
                                : hasGlobalKey || workflowsWithKeys.has(workflow.name ?? '')
                                ? 'bg-green-600 hover:bg-green-700'
                                : 'text-muted-foreground hover:bg-accent'
                            }`}
                            onClick={() => handleShowWebhook(workflow)}
                          >
                            {workflow.publicEndpoint ? (
                              <AlertTriangle className="mr-1 h-2 w-2" />
                            ) : (
                              <Webhook className="mr-1 h-2 w-2" />
                            )}
                            Endpoint
                          </Badge>
                        )}
                        {workflow.category && (
                          <Badge variant="secondary" className="text-xs">{workflow.category}</Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        onClick={() => handleExecute(workflow.name ?? '')}
                      >
                        <PlayCircle className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Code className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">
              {searchTerm ? 'No workflows match your search' : 'No workflows available'}
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {searchTerm
                ? 'Try adjusting your search term or clear the filter'
                : 'No workflows have been registered in the workflow engine'
              }
            </p>
          </CardContent>
        </Card>
      )}

      {/* HTTP Trigger Dialog */}
      {selectedWorkflow && (
        <HttpTriggerDialog
          workflow={selectedWorkflow}
          open={webhookDialogOpen}
          onOpenChange={setWebhookDialogOpen}
        />
      )}
    </div>
  )
}
