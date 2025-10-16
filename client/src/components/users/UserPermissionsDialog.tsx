import { useState, useEffect } from 'react'
import { Shield, Check } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import { useOrganizations } from '@/hooks/useOrganizations'
import { useOrgPermissions, useGrantPermissions, useRevokePermissions } from '@/hooks/useUsers'
import type { components } from '@/lib/v1'
type User = components['schemas']['User']

interface PermissionsData {
  canExecuteWorkflows: boolean
  canManageConfig: boolean
  canManageForms: boolean
  canViewHistory: boolean
}

interface UserPermissionsDialogProps {
  user?: User | undefined
  open: boolean
  onClose: () => void
}

export function UserPermissionsDialog({ user, open, onClose }: UserPermissionsDialogProps) {
  const { data: organization, isLoading: orgsLoading } = useOrganizations()
  const organizations = organization ? [organization] : []
  const [selectedOrgId, setSelectedOrgId] = useState<string | undefined>()
  const [permissions, setPermissions] = useState<PermissionsData>({
    canExecuteWorkflows: false,
    canManageConfig: false,
    canManageForms: false,
    canViewHistory: false,
  })

  const { data: orgPermissions, isLoading: permsLoading } = useOrgPermissions(selectedOrgId)
  
  const orgPermissionsArray = (orgPermissions as { userId: string; orgId: string }[]) || []
  const grantMutation = useGrantPermissions()
  const revokeMutation = useRevokePermissions()

  // Reset state when dialog opens/closes or user changes
  useEffect(() => {
    if (open && user) {
      setSelectedOrgId(undefined)
      setPermissions({
        canExecuteWorkflows: false,
        canManageConfig: false,
        canManageForms: false,
        canViewHistory: false,
      })
    }
  }, [open, user])

  // Find user's current permissions for selected org
  useEffect(() => {
    // Permissions system is deprecated, always set to false
    if (user) {
      setPermissions({
        canExecuteWorkflows: false,
        canManageConfig: false,
        canManageForms: false,
        canViewHistory: false,
      })
    }
  }, [user])

  if (!user) return null

  const handleSave = async () => {
    if (!selectedOrgId) return

    // Check if any permissions are enabled
    const hasAnyPermission = Object.values(permissions).some((p) => p)

    if (hasAnyPermission) {
      await grantMutation.mutateAsync({
        userId: user.id,
        orgId: selectedOrgId,
        permissions,
      })
    } else {
      // If no permissions, revoke access
      await revokeMutation.mutateAsync({
        userId: user.id,
        orgId: selectedOrgId,
      })
    }

    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[700px]">
        <DialogHeader>
          <DialogTitle>Manage Permissions - {user.displayName}</DialogTitle>
          <DialogDescription>
            Grant or revoke organization access and permissions
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* MSP Users note */}
          {user.userType === 'PLATFORM' && (
            <Card className="border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-950">
              <CardContent className="pt-4">
                <div className="flex items-start gap-2">
                  <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                      MSP User - Full Access
                    </p>
                    <p className="text-sm text-blue-700 dark:text-blue-300">
                      MSP users have automatic access to all organizations. Organization-specific permissions do not apply.
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Organization Selection */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Select Organization</CardTitle>
              <CardDescription>
                Choose an organization to manage permissions
              </CardDescription>
            </CardHeader>
            <CardContent>
              {orgsLoading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : organizations && organizations.length > 0 ? (
                <div className="space-y-2">
                  {organizations.map((org) => {
                    const hasAccess = orgPermissionsArray.some((p) => p.userId === user.id && p.orgId === org.id)
                    return (
                      <button
                        key={org.id}
                        onClick={() => setSelectedOrgId(org.id)}
                        className={`w-full text-left rounded-lg border p-3 transition-colors ${
                          selectedOrgId === org.id
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:border-primary/50'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-medium">{org.name}</p>
                            <p className="text-sm text-muted-foreground">
                              {org.tenantId || 'No tenant ID'}
                            </p>
                          </div>
                          <div className="flex items-center gap-2">
                            {hasAccess && (
                              <Badge variant="default" className="bg-green-500">
                                <Check className="mr-1 h-3 w-3" />
                                Has Access
                              </Badge>
                            )}
                            {selectedOrgId === org.id && (
                              <Badge variant="default">Selected</Badge>
                            )}
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No organizations found
                </p>
              )}
            </CardContent>
          </Card>

          {/* Permissions Configuration */}
          {selectedOrgId && user.userType === 'ORG' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Permissions</CardTitle>
                <CardDescription>
                  Configure what the user can do in this organization
                </CardDescription>
              </CardHeader>
              <CardContent>
                {permsLoading ? (
                  <div className="space-y-2">
                    {[...Array(4)].map((_, i) => (
                      <Skeleton key={i} className="h-10 w-full" />
                    ))}
                  </div>
                ) : (
                  <div className="space-y-4">
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="executeWorkflows"
                        checked={permissions.canExecuteWorkflows}
                        onCheckedChange={(checked) =>
                          setPermissions({ ...permissions, canExecuteWorkflows: !!checked })
                        }
                      />
                      <label
                        htmlFor="executeWorkflows"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        Execute Workflows
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="manageConfig"
                        checked={permissions.canManageConfig}
                        onCheckedChange={(checked) =>
                          setPermissions({ ...permissions, canManageConfig: !!checked })
                        }
                      />
                      <label
                        htmlFor="manageConfig"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        Manage Configuration
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="manageForms"
                        checked={permissions.canManageForms}
                        onCheckedChange={(checked) =>
                          setPermissions({ ...permissions, canManageForms: !!checked })
                        }
                      />
                      <label
                        htmlFor="manageForms"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        Manage Forms
                      </label>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Checkbox
                        id="viewHistory"
                        checked={permissions.canViewHistory}
                        onCheckedChange={(checked) =>
                          setPermissions({ ...permissions, canViewHistory: !!checked })
                        }
                      />
                      <label
                        htmlFor="viewHistory"
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        View Execution History
                      </label>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* Action Buttons */}
          {selectedOrgId && user.userType === 'ORG' && (
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button
                onClick={handleSave}
                disabled={grantMutation.isPending || revokeMutation.isPending}
              >
                {grantMutation.isPending || revokeMutation.isPending ? 'Saving...' : 'Save Permissions'}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
