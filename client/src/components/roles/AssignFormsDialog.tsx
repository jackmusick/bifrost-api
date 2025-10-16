import { useState } from 'react'
import { FileCode } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useForms } from '@/hooks/useForms'
import { useAssignFormsToRole } from '@/hooks/useRoles'
import type { components } from '@/lib/v1'
type Role = components['schemas']['Role']

interface AssignFormsDialogProps {
  role?: Role | undefined
  open: boolean
  onClose: () => void
}

export function AssignFormsDialog({ role, open, onClose }: AssignFormsDialogProps) {
  const [selectedFormIds, setSelectedFormIds] = useState<string[]>([])

  const { data: forms, isLoading } = useForms()
  const assignForms = useAssignFormsToRole()

  const handleToggleForm = (formId: string) => {
    setSelectedFormIds((prev) =>
      prev.includes(formId)
        ? prev.filter((id) => id !== formId)
        : [...prev, formId]
    )
  }

  const handleAssign = async () => {
    if (!role || selectedFormIds.length === 0) return

    await assignForms.mutateAsync({
      roleId: role.id,
      request: { formIds: selectedFormIds },
    })

    setSelectedFormIds([])
    onClose()
  }

  const handleClose = () => {
    setSelectedFormIds([])
    onClose()
  }

  if (!role) return null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Assign Forms to Role</DialogTitle>
          <DialogDescription>
            Select forms that users with "{role.name}" role can access
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[400px] overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : forms && forms.length > 0 ? (
            <div className="space-y-2">
              {forms.map((form) => {
                const isSelected = selectedFormIds.includes(form.id)
                return (
                  <button
                    key={form.id}
                    onClick={() => handleToggleForm(form.id)}
                    className={`w-full rounded-lg border p-4 text-left transition-colors ${
                      isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-accent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{form.name}</p>
                        <p className="text-sm text-muted-foreground">
                          {form.description || `Workflow: ${form.linkedWorkflow}`}
                        </p>
                        <div className="mt-1 flex gap-2">
                          {form.isGlobal && (
                            <Badge variant="secondary" className="text-xs">
                              Global
                            </Badge>
                          )}
                          <Badge variant={form.isActive ? 'default' : 'outline'} className="text-xs">
                            {form.isActive ? 'Active' : 'Inactive'}
                          </Badge>
                        </div>
                      </div>
                      {isSelected && <Badge>Selected</Badge>}
                    </div>
                  </button>
                )
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <FileCode className="h-12 w-12 text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">
                No forms available
              </p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            onClick={handleAssign}
            disabled={selectedFormIds.length === 0 || assignForms.isPending}
          >
            {assignForms.isPending
              ? 'Assigning...'
              : `Assign ${selectedFormIds.length} Form${selectedFormIds.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
