import { useState } from 'react'
import { UserPlus } from 'lucide-react'
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
import { useUsers } from '@/hooks/useUsers'
import { useAssignUsersToRole } from '@/hooks/useRoles'
import type { components } from '@/lib/v1'
type Role = components['schemas']['Role']
type User = components['schemas']['User']

interface AssignUsersDialogProps {
  role?: Role | undefined
  open: boolean
  onClose: () => void
}

export function AssignUsersDialog({ role, open, onClose }: AssignUsersDialogProps) {
  const [selectedUserIds, setSelectedUserIds] = useState<string[]>([])

  // Only fetch ORG users (MSP users cannot be assigned to roles)
  const { data: users, isLoading } = useUsers('org')
  const assignUsers = useAssignUsersToRole()

  const handleToggleUser = (userId: string) => {
    setSelectedUserIds((prev) =>
      prev.includes(userId)
        ? prev.filter((id) => id !== userId)
        : [...prev, userId]
    )
  }

  const handleAssign = async () => {
    if (!role || selectedUserIds.length === 0) return

    await assignUsers.mutateAsync({
      roleId: role.id,
      request: { userIds: selectedUserIds },
    })

    setSelectedUserIds([])
    onClose()
  }

  const handleClose = () => {
    setSelectedUserIds([])
    onClose()
  }

  if (!role) return null

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Assign Users to Role</DialogTitle>
          <DialogDescription>
            Select organization users to assign to "{role.name}"
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[400px] overflow-y-auto">
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : users && users.length > 0 ? (
            <div className="space-y-2">
              {users.map((user: User) => {
                const isSelected = selectedUserIds.includes(user.id)
                return (
                  <button
                    key={user.id}
                    onClick={() => handleToggleUser(user.id)}
                    className={`w-full rounded-lg border p-4 text-left transition-colors ${
                      isSelected
                        ? 'border-primary bg-primary/5'
                        : 'border-border hover:bg-accent'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium">{user.displayName}</p>
                        <p className="text-sm text-muted-foreground">{user.email}</p>
                      </div>
                      {isSelected && <Badge>Selected</Badge>}
                    </div>
                  </button>
                )
              })}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <UserPlus className="h-12 w-12 text-muted-foreground" />
              <p className="mt-2 text-sm text-muted-foreground">
                No organization users available
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
            disabled={selectedUserIds.length === 0 || assignUsers.isPending}
          >
            {assignUsers.isPending
              ? 'Assigning...'
              : `Assign ${selectedUserIds.length} User${selectedUserIds.length !== 1 ? 's' : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
