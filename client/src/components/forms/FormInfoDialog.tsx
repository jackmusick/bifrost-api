import { useEffect, useState } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
import { useWorkflowsMetadata } from '@/hooks/useWorkflows'
import type { components } from '@/lib/v1'

type WorkflowParameter = components['schemas']['WorkflowParameter']

interface FormInfoDialogProps {
  open: boolean
  onClose: () => void
  onSave: (info: {
    formName: string
    formDescription: string
    linkedWorkflow: string
    launchWorkflowId: string | null
    defaultLaunchParams: Record<string, unknown> | null
  }) => void
  initialData?: {
    formName: string
    formDescription: string
    linkedWorkflow: string
    launchWorkflowId?: string | null
    defaultLaunchParams?: Record<string, unknown> | null
  }
}

export function FormInfoDialog({ open, onClose, onSave, initialData }: FormInfoDialogProps) {
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [linkedWorkflow, setLinkedWorkflow] = useState('')
  const [launchWorkflowId, setLaunchWorkflowId] = useState<string>('')
  const [defaultLaunchParams, setDefaultLaunchParams] = useState<Record<string, unknown>>({})

  const { data: metadata, isLoading: metadataLoading } = useWorkflowsMetadata()

  // Get selected launch workflow metadata
  const selectedLaunchWorkflow = metadata?.workflows?.find(w => w.name === launchWorkflowId)
  const launchWorkflowParams = selectedLaunchWorkflow?.parameters || []

  useEffect(() => {
    if (initialData) {
      setFormName(initialData.formName)
      setFormDescription(initialData.formDescription)
      setLinkedWorkflow(initialData.linkedWorkflow)
      setLaunchWorkflowId(initialData.launchWorkflowId || '')
      setDefaultLaunchParams((initialData.defaultLaunchParams as Record<string, unknown>) || {})
    }
  }, [initialData, open])

  // Clear default params when launch workflow changes
  useEffect(() => {
    if (!launchWorkflowId || launchWorkflowId === '__none__') {
      setDefaultLaunchParams({})
    }
  }, [launchWorkflowId])

  const handleParameterChange = (paramName: string, value: unknown) => {
    setDefaultLaunchParams((prev) => ({
      ...prev,
      [paramName]: value,
    }))
  }

  const renderParameterInput = (param: WorkflowParameter) => {
    const value = defaultLaunchParams[param.name ?? '']

    switch (param.type) {
      case 'bool':
        return (
          <div className="flex items-center space-x-2">
            <Checkbox
              id={`param-${param.name}`}
              checked={!!value}
              onCheckedChange={(checked) => handleParameterChange(param.name ?? '', checked)}
            />
            <Label htmlFor={`param-${param.name}`} className="text-sm font-normal">
              {param.name}
              {param.required && <span className="text-destructive ml-1">*</span>}
              {!param.required && (
                <Badge variant="secondary" className="text-[10px] px-1 py-0 ml-2">Optional</Badge>
              )}
              {param.description && (
                <span className="block text-xs text-muted-foreground mt-1">
                  {param.description}
                </span>
              )}
            </Label>
          </div>
        )

      case 'int':
      case 'float':
        return (
          <div className="space-y-1.5">
            <Label htmlFor={`param-${param.name}`} className="text-sm flex items-center gap-2">
              {param.name}
              {param.required && (
                <Badge variant="destructive" className="text-[10px] px-1 py-0">Required</Badge>
              )}
              {!param.required && (
                <Badge variant="secondary" className="text-[10px] px-1 py-0">Optional</Badge>
              )}
            </Label>
            <Input
              id={`param-${param.name}`}
              type="number"
              step={param.type === 'float' ? '0.1' : '1'}
              value={value as string | number | undefined ?? ''}
              onChange={(e) =>
                handleParameterChange(
                  param.name ?? '',
                  param.type === 'int' ? parseInt(e.target.value) : parseFloat(e.target.value)
                )
              }
              placeholder={param.description || `Enter default value for ${param.name}`}
            />
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
          </div>
        )

      case 'list':
        return (
          <div className="space-y-1.5">
            <Label htmlFor={`param-${param.name}`} className="text-sm flex items-center gap-2">
              {param.name}
              {param.required && (
                <Badge variant="destructive" className="text-[10px] px-1 py-0">Required</Badge>
              )}
              {!param.required && (
                <Badge variant="secondary" className="text-[10px] px-1 py-0">Optional</Badge>
              )}
            </Label>
            <Input
              id={`param-${param.name}`}
              type="text"
              value={Array.isArray(value) ? value.join(', ') : (value as string ?? '')}
              onChange={(e) =>
                handleParameterChange(
                  param.name ?? '',
                  e.target.value.split(',').map((v) => v.trim())
                )
              }
              placeholder={param.description || "Comma-separated values"}
            />
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
          </div>
        )

      default:
        // string, email, json
        return (
          <div className="space-y-1.5">
            <Label htmlFor={`param-${param.name}`} className="text-sm flex items-center gap-2">
              {param.name}
              {param.required && (
                <Badge variant="destructive" className="text-[10px] px-1 py-0">Required</Badge>
              )}
              {!param.required && (
                <Badge variant="secondary" className="text-[10px] px-1 py-0">Optional</Badge>
              )}
            </Label>
            <Input
              id={`param-${param.name}`}
              type={param.type === 'email' ? 'email' : 'text'}
              value={(value as string) ?? ''}
              onChange={(e) => handleParameterChange(param.name ?? '', e.target.value)}
              placeholder={param.description || `Enter default value for ${param.name}`}
            />
            {param.description && (
              <p className="text-xs text-muted-foreground">{param.description}</p>
            )}
          </div>
        )
    }
  }

  const handleSave = () => {
    // Handle "__none__" special value for launch workflow
    const finalLaunchWorkflowId = launchWorkflowId === '__none__' || !launchWorkflowId.trim()
      ? null
      : launchWorkflowId.trim()

    // Only include defaultLaunchParams if launch workflow is set and params exist
    const finalDefaultParams = finalLaunchWorkflowId && Object.keys(defaultLaunchParams).length > 0
      ? defaultLaunchParams
      : null

    onSave({
      formName,
      formDescription,
      linkedWorkflow,
      launchWorkflowId: finalLaunchWorkflowId,
      defaultLaunchParams: finalDefaultParams,
    })
    onClose()
  }

  const isSaveDisabled = !formName || !linkedWorkflow

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Form Information</DialogTitle>
          <DialogDescription>
            Configure basic details about the form and linked workflow
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="formName">Form Name *</Label>
            <Input
              id="formName"
              placeholder="User Onboarding Form"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="linkedWorkflow">Linked Workflow *</Label>
            {metadataLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={linkedWorkflow} onValueChange={setLinkedWorkflow}>
                <SelectTrigger id="linkedWorkflow">
                  <SelectValue placeholder="Select a workflow" />
                </SelectTrigger>
                <SelectContent>
                  {metadata?.workflows?.map((workflow) => (
                    <SelectItem key={workflow.name ?? 'unknown'} value={workflow.name ?? ''}>
                      <div className="flex flex-col">
                        <span className="font-medium">{workflow.name ?? 'Unnamed'}</span>
                        <span className="text-xs text-muted-foreground">
                          {workflow.description ?? ''}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <p className="text-xs text-muted-foreground">
              The workflow that will be executed when this form is submitted
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="formDescription">Description</Label>
            <Textarea
              id="formDescription"
              placeholder="Describe what this form does..."
              value={formDescription}
              onChange={(e) => setFormDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="launchWorkflowId">Launch Workflow (Optional)</Label>
            {metadataLoading ? (
              <Skeleton className="h-10 w-full" />
            ) : (
              <Select value={launchWorkflowId} onValueChange={setLaunchWorkflowId}>
                <SelectTrigger id="launchWorkflowId">
                  <SelectValue placeholder="Select a workflow (or leave empty)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__none__">None</SelectItem>
                  {metadata?.workflows?.map((workflow) => (
                    <SelectItem key={workflow.name ?? 'unknown'} value={workflow.name ?? ''}>
                      <div className="flex flex-col">
                        <span className="font-medium">{workflow.name ?? 'Unnamed'}</span>
                        <span className="text-xs text-muted-foreground">
                          {workflow.description ?? ''}
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
            <p className="text-xs text-muted-foreground">
              Workflow to execute when form loads (results available in context.workflow)
            </p>
          </div>

          {/* Default Launch Parameters */}
          {launchWorkflowId && launchWorkflowId !== '__none__' && launchWorkflowParams.length > 0 && (
            <div className="space-y-3 rounded-lg border p-4 bg-muted/50">
              <div>
                <Label className="text-sm font-medium">Default Launch Parameters</Label>
                <p className="text-xs text-muted-foreground mt-1">
                  Set default values for workflow parameters. Required parameters must have either a default value or a form field with "Allow as Query Param" enabled.
                </p>
              </div>
              <div className="space-y-3">
                {launchWorkflowParams.map((param) => (
                  <div key={param.name}>
                    {renderParameterInput(param)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaveDisabled}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
