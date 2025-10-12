import { UserCog, FileCode, Shield, Clock } from 'lucide-react'
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
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useUserRoles, useUserForms } from '@/hooks/useUsers'
import type { User } from '@/types/user'

interface UserDetailsDialogProps {
  user?: User | undefined
  open: boolean
  onClose: () => void
}

export function UserDetailsDialog({ user, open, onClose }: UserDetailsDialogProps) {
  const { data: roles, isLoading: rolesLoading } = useUserRoles(user?.id)
  const { data: formsAccess, isLoading: formsLoading } = useUserForms(user?.id)

  if (!user) return null

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>{user.displayName}</DialogTitle>
          <DialogDescription>
            {user.email} • {user.userType === 'PLATFORM' ? 'MSP Technician' : 'Organization User'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* User Info Card */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">User Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">User Type</span>
                <Badge variant={user.userType === 'PLATFORM' ? 'default' : 'secondary'}>
                  {user.userType === 'PLATFORM' ? (
                    <>
                      <Shield className="mr-1 h-3 w-3" />
                      MSP Technician
                    </>
                  ) : (
                    'Organization User'
                  )}
                </Badge>
              </div>

              {user.userType === 'PLATFORM' && (
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">MSP Admin</span>
                  <Badge variant={user.isPlatformAdmin ? 'destructive' : 'outline'}>
                    {user.isPlatformAdmin ? 'Yes' : 'No'}
                  </Badge>
                </div>
              )}

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Status</span>
                <Badge variant={user.isActive ? 'default' : 'secondary'}>
                  {user.isActive ? 'Active' : 'Inactive'}
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Last Login</span>
                <span className="text-sm flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  {user.lastLogin
                    ? new Date(user.lastLogin).toLocaleString()
                    : 'Never logged in'}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Created</span>
                <span className="text-sm">{new Date(user.createdAt).toLocaleDateString()}</span>
              </div>
            </CardContent>
          </Card>

          {/* Roles and Forms Tabs (only for ORG users) */}
          {user.userType === 'ORG' && (
            <Tabs defaultValue="roles">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="roles">
                  <UserCog className="mr-2 h-4 w-4" />
                  Roles
                </TabsTrigger>
                <TabsTrigger value="forms">
                  <FileCode className="mr-2 h-4 w-4" />
                  Form Access
                </TabsTrigger>
              </TabsList>

              <TabsContent value="roles" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Assigned Roles</CardTitle>
                    <CardDescription>
                      Roles determine which forms this user can access
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {rolesLoading ? (
                      <div className="space-y-2">
                        {[...Array(2)].map((_, i) => (
                          <Skeleton key={i} className="h-10 w-full" />
                        ))}
                      </div>
                    ) : roles && roles.length > 0 ? (
                      <div className="space-y-2">
                        {roles.map((userRole) => (
                          <div
                            key={userRole.roleId}
                            className="flex items-center justify-between rounded-lg border p-3"
                          >
                            <div>
                              <p className="font-medium">{userRole.roleId}</p>
                              <p className="text-sm text-muted-foreground">
                                Assigned {new Date(userRole.assignedAt).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center py-8 text-center">
                        <UserCog className="h-12 w-12 text-muted-foreground" />
                        <p className="mt-2 text-sm text-muted-foreground">
                          No roles assigned to this user
                        </p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="forms" className="mt-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Form Access</CardTitle>
                    <CardDescription>
                      Forms this user can execute based on their roles
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {formsLoading ? (
                      <div className="space-y-2">
                        {[...Array(2)].map((_, i) => (
                          <Skeleton key={i} className="h-10 w-full" />
                        ))}
                      </div>
                    ) : formsAccess ? (
                      formsAccess.hasAccessToAllForms ? (
                        <div className="rounded-lg border border-green-200 bg-green-50 p-4 dark:border-green-800 dark:bg-green-950">
                          <p className="text-sm font-medium text-green-900 dark:text-green-100">
                            Full Access
                          </p>
                          <p className="text-sm text-green-700 dark:text-green-300">
                            This user has access to all forms
                          </p>
                        </div>
                      ) : formsAccess.formIds.length > 0 ? (
                        <div className="space-y-2">
                          {formsAccess.formIds.map((formId) => (
                            <div
                              key={formId}
                              className="rounded-lg border p-3"
                            >
                              <p className="font-medium">{formId}</p>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="flex flex-col items-center justify-center py-8 text-center">
                          <FileCode className="h-12 w-12 text-muted-foreground" />
                          <p className="mt-2 text-sm text-muted-foreground">
                            No forms accessible to this user
                          </p>
                        </div>
                      )
                    ) : null}
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          )}

          {/* MSP users have full access */}
          {user.userType === 'PLATFORM' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Access Level</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 dark:border-blue-800 dark:bg-blue-950">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                    Full Platform Access
                  </p>
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    {user.isPlatformAdmin
                      ? 'MSP Admin - Full access to all platform features'
                      : 'MSP Technician - Access to manage workflows and configurations'}
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
