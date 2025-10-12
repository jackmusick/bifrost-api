import { useEffect, useState } from 'react'
import { Shield } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { useUserRoles } from '@/hooks/useUsers'
import { useRoles, useAssignUsersToRole, useRemoveUserFromRole } from '@/hooks/useRoles'
import type { User } from '@/types/user'
import { toast } from 'sonner'

interface UserRolesDialogProps {
  user: User | undefined
  open: boolean
  onClose: () => void
}

export function UserRolesDialog({ user, open, onClose }: UserRolesDialogProps) {
  const { data: userRoles, isLoading: rolesLoading } = useUserRoles(user?.id)
  const { data: allRoles, isLoading: allRolesLoading } = useRoles()
  const assignMutation = useAssignUsersToRole()
  const removeMutation = useRemoveUserFromRole()

  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set())

  // Initialize selected roles when data loads
  useEffect(() => {
    if (userRoles) {
      setSelectedRoles(new Set(userRoles.roleIds || []))
    }
  }, [userRoles])

  const handleToggleRole = async (roleId: string, checked: boolean) => {
    if (!user) return

    try {
      if (checked) {
        // Assign role (useAssignUsersToRole expects { roleId, request: { userIds } })
        await assignMutation.mutateAsync({
          roleId,
          request: { userIds: [user.id] }
        })
        setSelectedRoles(prev => new Set([...prev, roleId]))
      } else {
        // Remove role
        await removeMutation.mutateAsync({ roleId, userId: user.id })
        setSelectedRoles(prev => {
          const next = new Set(prev)
          next.delete(roleId)
          return next
        })
      }
    } catch (error) {
      toast.error(`Failed to ${checked ? 'assign' : 'remove'} role`)
    }
  }

  if (!user) return null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Manage Roles - {user.displayName}
          </DialogTitle>
          <DialogDescription>
            Assign or remove roles for this user. Roles determine which forms the user can access.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {rolesLoading || allRolesLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : allRoles && allRoles.length > 0 ? (
            <div className="space-y-3">
              {allRoles.map((role) => {
                const isAssigned = selectedRoles.has(role.id)
                return (
                  <div
                    key={role.id}
                    className="flex items-start space-x-3 rounded-lg border p-4 hover:bg-accent/50 transition-colors"
                  >
                    <Checkbox
                      id={role.id}
                      checked={isAssigned}
                      onCheckedChange={(checked) => handleToggleRole(role.id, checked as boolean)}
                      disabled={assignMutation.isPending || removeMutation.isPending}
                    />
                    <div className="flex-1 space-y-1">
                      <Label
                        htmlFor={role.id}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {role.name}
                        {role.scope === 'GLOBAL' && (
                          <Badge variant="outline" className="ml-2">
                            Global
                          </Badge>
                        )}
                      </Label>
                      {role.description && (
                        <p className="text-sm text-muted-foreground">{role.description}</p>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              No roles available
            </div>
          )}
        </div>

        <div className="flex justify-end">
          <Button onClick={onClose}>Close</Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
