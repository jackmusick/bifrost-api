import { useState } from 'react'
import { Users, FileCode, X, UserPlus, FilePlus } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useRoleUsers, useRoleForms, useRemoveUserFromRole, useRemoveFormFromRole } from '@/hooks/useRoles'
import { AssignUsersDialog } from './AssignUsersDialog'
import { AssignFormsDialog } from './AssignFormsDialog'
import type { Role } from '@/types/role'

interface RoleDetailsDialogProps {
  role?: Role | undefined
  open: boolean
  onClose: () => void
}

export function RoleDetailsDialog({ role, open, onClose }: RoleDetailsDialogProps) {
  const [isAssignUsersOpen, setIsAssignUsersOpen] = useState(false)
  const [isAssignFormsOpen, setIsAssignFormsOpen] = useState(false)

  const { data: users, isLoading: usersLoading } = useRoleUsers(role?.id)
  const { data: forms, isLoading: formsLoading } = useRoleForms(role?.id)
  const removeUser = useRemoveUserFromRole()
  const removeForm = useRemoveFormFromRole()

  if (!role) return null

  const handleRemoveUser = (userId: string) => {
    if (confirm('Remove this user from the role?')) {
      removeUser.mutate({ roleId: role.id, userId })
    }
  }

  const handleRemoveForm = (formId: string) => {
    if (confirm('Remove this form from the role?')) {
      removeForm.mutate({ roleId: role.id, formId })
    }
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{role.name}</DialogTitle>
          <DialogDescription>
            {role.description || 'Manage users and forms for this role'}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="users" className="mt-4">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="users">
              <Users className="mr-2 h-4 w-4" />
              Users
            </TabsTrigger>
            <TabsTrigger value="forms">
              <FileCode className="mr-2 h-4 w-4" />
              Forms
            </TabsTrigger>
          </TabsList>

          <TabsContent value="users" className="mt-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Assigned Users</CardTitle>
                    <CardDescription>
                      Organization users who have this role
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAssignUsersOpen(true)}
                  >
                    <UserPlus className="mr-2 h-4 w-4" />
                    Assign Users
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {usersLoading ? (
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : users && users.length > 0 ? (
                  <div className="space-y-2">
                    {users.map((userRole) => (
                      <div
                        key={userRole.userId}
                        className="flex items-center justify-between rounded-lg border p-3"
                      >
                        <div>
                          <p className="font-medium">{userRole.userId}</p>
                          <p className="text-sm text-muted-foreground">
                            Assigned {new Date(userRole.assignedAt).toLocaleDateString()}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveUser(userRole.userId)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <Users className="h-12 w-12 text-muted-foreground" />
                    <p className="mt-2 text-sm text-muted-foreground">
                      No users assigned to this role
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="forms" className="mt-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Assigned Forms</CardTitle>
                    <CardDescription>
                      Forms that users with this role can access
                    </CardDescription>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setIsAssignFormsOpen(true)}
                  >
                    <FilePlus className="mr-2 h-4 w-4" />
                    Assign Forms
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {formsLoading ? (
                  <div className="space-y-2">
                    {[...Array(3)].map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : forms && forms.length > 0 ? (
                  <div className="space-y-2">
                    {forms.map((formRole) => (
                      <div
                        key={formRole.formId}
                        className="flex items-center justify-between rounded-lg border p-3"
                      >
                        <div>
                          <p className="font-medium">{formRole.formId}</p>
                          <p className="text-sm text-muted-foreground">
                            Assigned {new Date(formRole.assignedAt).toLocaleDateString()}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleRemoveForm(formRole.formId)}
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center py-8 text-center">
                    <FileCode className="h-12 w-12 text-muted-foreground" />
                    <p className="mt-2 text-sm text-muted-foreground">
                      No forms assigned to this role
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DialogContent>

      <AssignUsersDialog
        role={role}
        open={isAssignUsersOpen}
        onClose={() => setIsAssignUsersOpen(false)}
      />

      <AssignFormsDialog
        role={role}
        open={isAssignFormsOpen}
        onClose={() => setIsAssignFormsOpen(false)}
      />
    </Dialog>
  )
}
