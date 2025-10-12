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
import { useWorkflowsMetadata } from '@/hooks/useWorkflows'

interface FormInfoDialogProps {
  open: boolean
  onClose: () => void
  onSave: (info: {
    formName: string
    formDescription: string
    linkedWorkflow: string
    isGlobal: boolean
  }) => void
  initialData?: {
    formName: string
    formDescription: string
    linkedWorkflow: string
    isGlobal: boolean
  }
}

export function FormInfoDialog({ open, onClose, onSave, initialData }: FormInfoDialogProps) {
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [linkedWorkflow, setLinkedWorkflow] = useState('')
  const [isGlobal, setIsGlobal] = useState(false)

  const { data: metadata, isLoading: metadataLoading } = useWorkflowsMetadata()

  useEffect(() => {
    if (initialData) {
      setFormName(initialData.formName)
      setFormDescription(initialData.formDescription)
      setLinkedWorkflow(initialData.linkedWorkflow)
      setIsGlobal(initialData.isGlobal)
    }
  }, [initialData, open])

  const handleSave = () => {
    onSave({
      formName,
      formDescription,
      linkedWorkflow,
      isGlobal,
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
            <Label>Scope</Label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setIsGlobal(true)}
                className={`flex-1 rounded-lg border p-3 text-left transition-colors ${
                  isGlobal
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'border-border hover:bg-accent'
                }`}
              >
                <Badge variant={isGlobal ? 'default' : 'outline'} className="mb-1">
                  Global
                </Badge>
                <p className="text-xs text-muted-foreground">
                  Available to all organizations
                </p>
              </button>
              <button
                type="button"
                onClick={() => setIsGlobal(false)}
                className={`flex-1 rounded-lg border p-3 text-left transition-colors ${
                  !isGlobal
                    ? 'border-primary bg-primary/5 text-primary'
                    : 'border-border hover:bg-accent'
                }`}
              >
                <Badge variant={!isGlobal ? 'default' : 'outline'} className="mb-1">
                  Organization
                </Badge>
                <p className="text-xs text-muted-foreground">
                  Specific to one organization
                </p>
              </button>
            </div>
          </div>
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
