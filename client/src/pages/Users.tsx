import { useState } from 'react'
import { Shield, Users as UsersIcon, RefreshCw, UserCog, Eye, Edit } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useUsers } from '@/hooks/useUsers'
import { UserDetailsDialog } from '@/components/users/UserDetailsDialog'
import { UserRolesDialog } from '@/components/users/UserRolesDialog'
import type { components } from '@/lib/v1'
type User = components['schemas']['User']

export function Users() {
  const [selectedUser, setSelectedUser] = useState<User | undefined>()
  const [isDetailsOpen, setIsDetailsOpen] = useState(false)
  const [isRolesOpen, setIsRolesOpen] = useState(false)

  // Get ALL users (no type filter) to avoid duplication
  const { data: users, isLoading, refetch} = useUsers()

  const handleViewDetails = (user: User) => {
    setSelectedUser(user)
    setIsDetailsOpen(true)
  }

  const handleEditRoles = (user: User) => {
    setSelectedUser(user)
    setIsRolesOpen(true)
  }

  const handleDetailsClose = () => {
    setIsDetailsOpen(false)
    setSelectedUser(undefined)
  }

  const handleRolesClose = () => {
    setIsRolesOpen(false)
    setSelectedUser(undefined)
  }

  const getUserTypeBadge = (type: string) => {
    return type === 'PLATFORM' ? (
      <Badge variant="default">
        <Shield className="mr-1 h-3 w-3" />
        Platform
      </Badge>
    ) : (
      <Badge variant="secondary">
        <UsersIcon className="mr-1 h-3 w-3" />
        Organization
      </Badge>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-extrabold tracking-tight">Users</h1>
          <p className="mt-2 text-muted-foreground">
            Manage platform administrators and organization users
          </p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Users</CardTitle>
              <CardDescription>
                Platform administrators and organization users
              </CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : users && users.length > 0 ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Admin</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">{user.displayName}</TableCell>
                    <TableCell className="text-muted-foreground">{user.email}</TableCell>
                    <TableCell>{getUserTypeBadge(user.userType)}</TableCell>
                    <TableCell>
                      {user.isPlatformAdmin ? (
                        <Badge variant="destructive">Admin</Badge>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge variant={user.isActive ? 'default' : 'secondary'}>
                        {user.isActive ? 'Active' : 'Inactive'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {user.lastLogin
                        ? new Date(user.lastLogin).toLocaleDateString()
                        : 'Never'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleEditRoles(user)}
                          title="Manage roles"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        {/* Permissions button removed */}
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleViewDetails(user)}
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <UserCog className="h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No users found</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                No users in the system
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      <UserDetailsDialog
        user={selectedUser}
        open={isDetailsOpen}
        onClose={handleDetailsClose}
      />

      {/* UserPermissionsDialog removed */}

      <UserRolesDialog
        user={selectedUser}
        open={isRolesOpen}
        onClose={handleRolesClose}
      />
    </div>
  )
}
