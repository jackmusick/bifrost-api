import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PlayCircle, Code, RefreshCw, Webhook } from 'lucide-react'
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
import { useWorkflowsMetadata } from '@/hooks/useWorkflows'
import { HttpTriggerDialog } from '@/components/workflows/HttpTriggerDialog'
import type { Workflow } from '@/types/workflow'

export function Workflows() {
  const navigate = useNavigate()
  const { data, isLoading, refetch } = useWorkflowsMetadata()
  const [webhookDialogOpen, setWebhookDialogOpen] = useState(false)
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null)

  const workflows = data?.workflows || []

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
        <Button variant="outline" size="icon" onClick={() => refetch()}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : workflows.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((workflow) => (
            <Card key={workflow.name} className="hover:border-primary transition-colors flex flex-col">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span className="font-mono text-base">{workflow.name}</span>
                  <div className="flex items-center gap-1">
                    <Badge
                      variant="outline"
                      className="cursor-pointer hover:bg-accent"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleShowWebhook(workflow)
                      }}
                    >
                      <Webhook className="mr-1 h-3 w-3" />
                      HTTP
                    </Badge>
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
                  {workflow.tags && workflow.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {workflow.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}
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
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <Code className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">No workflows available</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              No workflows have been registered in the workflow engine
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
