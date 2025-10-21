import { useState, useEffect } from 'react'
import { Link2, Plus, RefreshCw, AlertTriangle, LayoutGrid, Table as TableIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { SearchBox } from '@/components/search/SearchBox'
import { useSearch } from '@/hooks/useSearch'
import {
  useOAuthConnections,
  useDeleteOAuthConnection,
  useAuthorizeOAuthConnection,
  useCancelOAuthAuthorization,
  useRefreshOAuthToken,
} from '@/hooks/useOAuth'
import { CreateOAuthConnectionDialog } from '@/components/oauth/CreateOAuthConnectionDialog'
import { OAuthConnectionCard } from '@/components/oauth/OAuthConnectionCard'
import { RefreshJobStatus } from '@/components/oauth/RefreshJobStatus'
import { getStatusLabel, isExpired, expiresSoon } from '@/lib/client-types'


export function OAuthConnections() {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editConnectionName, setEditConnectionName] = useState<string | undefined>(undefined)
  const [selectedOrgId] = useState<string | undefined>(undefined)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [connectionToDelete, setConnectionToDelete] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')

  const { data: connections, isLoading, refetch } = useOAuthConnections()
  const deleteMutation = useDeleteOAuthConnection()
  const authorizeMutation = useAuthorizeOAuthConnection()
  const cancelMutation = useCancelOAuthAuthorization()
  const refreshMutation = useRefreshOAuthToken()

  // Apply search filter
  const filteredConnections = useSearch(
    connections || [],
    searchTerm,
    [
      'connection_name',
      'oauth_flow_type',
      'status',
      (item) => item.status_message || ''
    ]
  )

  // Listen for OAuth success messages from popup window
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      // Verify origin for security
      if (event.origin !== window.location.origin) {
        return
      }

      // Check if this is an OAuth success message
      if (event.data?.type === 'oauth_success') {
        console.log('OAuth success received for connection:', event.data.connectionName)
        // Refresh connections list to show updated status
        refetch()
      }
    }

    window.addEventListener('message', handleMessage)

    // Cleanup listener on unmount
    return () => {
      window.removeEventListener('message', handleMessage)
    }
  }, [refetch])

  const handleCreate = () => {
    setEditConnectionName(undefined)
    setIsCreateDialogOpen(true)
  }

  const handleEdit = (connectionName: string) => {
    setEditConnectionName(connectionName)
    setIsCreateDialogOpen(true)
  }

  const handleRefresh = async (connectionName: string) => {
    try {
      await refreshMutation.mutateAsync(connectionName)
      refetch()
    } catch {
      // Error is already handled by the mutation's onError
    }
  }

  const handleAuthorize = async (connectionName: string): Promise<string | void> => {
    return new Promise((resolve) => {
      authorizeMutation.mutate(
        connectionName,
        {
          onSuccess: (response) => {
            // Open authorization URL in popup window
            const width = 600
            const height = 700
            const left = window.screenX + (window.outerWidth - width) / 2
            const top = window.screenY + (window.outerHeight - height) / 2
            window.open(
              response.authorization_url,
              'oauth_popup',
              `width=${width},height=${height},left=${left},top=${top},scrollbars=yes`
            )
            resolve(response.authorization_url)
          },
          onError: () => {
            resolve()
          }
        }
      )
    })
  }

  const handleCancel = async (connectionName: string) => {
    try {
      await cancelMutation.mutateAsync(connectionName)
      refetch()
    } catch {
      // Error is already handled by the mutation's onError
    }
  }

  const handleDelete = async (connectionName: string) => {
    setConnectionToDelete(connectionName)
    setDeleteDialogOpen(true)
  }

  const handleConfirmDelete = async () => {
    if (!connectionToDelete) return

    try {
      await deleteMutation.mutateAsync(connectionToDelete)
      refetch()
    } catch {
      // Error is already handled by the mutation's onError
    } finally {
      setDeleteDialogOpen(false)
      setConnectionToDelete(null)
    }
  }

  const getConnectionStats = () => {
    if (!connections) return { total: 0, connected: 0, failed: 0, pending: 0 }

    return {
      total: connections.length,
      connected: connections.filter((c) => c.status === 'completed').length,
      failed: connections.filter((c) => c.status === 'failed').length,
      pending: connections.filter((c) =>
        ['not_connected', 'waiting_callback', 'testing'].includes(c.status)
      ).length,
    }
  }

  const stats = getConnectionStats()

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight">OAuth Connections</h1>
            <p className="mt-2 text-muted-foreground">
              Manage OAuth 2.0 connections for workflows and integrations
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              Connect to external services like Microsoft Graph, Google APIs, GitHub, and more
            </p>
          </div>
          <div className="flex items-center gap-2">
            <ToggleGroup type="single" value={viewMode} onValueChange={(value: string) => value && setViewMode(value as 'grid' | 'table')}>
              <ToggleGroupItem value="grid" aria-label="Grid view" size="sm">
                <LayoutGrid className="h-4 w-4" />
              </ToggleGroupItem>
              <ToggleGroupItem value="table" aria-label="Table view" size="sm">
                <TableIcon className="h-4 w-4" />
              </ToggleGroupItem>
            </ToggleGroup>
            <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="outline" size="icon" onClick={handleCreate} title="New Connection">
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Search Box */}
      <SearchBox
        value={searchTerm}
        onChange={setSearchTerm}
        placeholder="Search OAuth connections by name, flow type, or status..."
        className="max-w-md"
      />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Connections</CardDescription>
            <CardTitle className="text-3xl">{stats.total}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Connected</CardDescription>
            <CardTitle className="text-3xl text-green-600">{stats.connected}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pending</CardDescription>
            <CardTitle className="text-3xl text-yellow-600">{stats.pending}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Failed</CardDescription>
            <CardTitle className="text-3xl text-red-600">{stats.failed}</CardTitle>
          </CardHeader>
        </Card>
        <RefreshJobStatus className="md:col-span-1" />
      </div>

      {/* Connections List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Your Connections</CardTitle>
              <CardDescription>
                {filteredConnections && filteredConnections.length > 0
                  ? `Showing ${filteredConnections.length} OAuth connection${filteredConnections.length !== 1 ? 's' : ''}`
                  : searchTerm ? 'No connections match your search' : 'No connections configured yet'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            viewMode === 'grid' ? (
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="h-48 w-full" />
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            )
          ) : filteredConnections && filteredConnections.length > 0 ? (
            viewMode === 'grid' ? (
              <div className="max-h-[calc(100vh-32rem)] overflow-auto">
                <div className="grid grid-cols-[repeat(auto-fill,minmax(320px,1fr))] gap-4 pb-4">
                  {filteredConnections.map((connection) => (
                    <OAuthConnectionCard
                      key={connection.connection_name}
                      connection={connection}
                      onAuthorize={handleAuthorize}
                      onEdit={handleEdit}
                      onRefresh={handleRefresh}
                      onCancel={handleCancel}
                      onDelete={handleDelete}
                      isAuthorizing={authorizeMutation.isPending}
                      isRefreshing={refreshMutation.isPending}
                      isCanceling={cancelMutation.isPending}
                      isDeleting={deleteMutation.isPending}
                    />
                  ))}
                </div>
              </div>
            ) : (
              <div className="max-h-[calc(100vh-32rem)] overflow-auto rounded-md border">
                <Table>
                  <TableHeader className="sticky top-0 bg-background z-10">
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Flow Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Refreshed</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredConnections.map((connection) => {
                      const expirationWarning = connection.expires_at && expiresSoon(connection.expires_at)
                      const isTokenExpired = connection.expires_at && isExpired(connection.expires_at)
                      const canConnect = connection.oauth_flow_type !== 'client_credentials'
                      const needsReconnection = connection.status === 'not_connected' || connection.status === 'failed'

                      return (
                        <TableRow key={connection.connection_name}>
                          <TableCell className="font-medium">{connection.connection_name}</TableCell>
                          <TableCell className="text-sm">{connection.oauth_flow_type.replace('_', ' ')}</TableCell>
                          <TableCell>
                            <div className="flex items-center gap-2">
                              <Badge
                                variant={
                                  connection.status === 'completed' ? 'default' :
                                  connection.status === 'failed' ? 'destructive' :
                                  connection.status === 'waiting_callback' || connection.status === 'testing' ? 'secondary' :
                                  'outline'
                                }
                                className="text-xs"
                              >
                                {getStatusLabel(connection.status)}
                              </Badge>
                              {isTokenExpired && <span className="text-xs text-red-600">Token expired</span>}
                              {!isTokenExpired && expirationWarning && <span className="text-xs text-yellow-600">Expires soon</span>}
                            </div>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">
                            {connection.last_refresh_at ? (
                              new Date(connection.last_refresh_at.endsWith('Z') ? connection.last_refresh_at : `${connection.last_refresh_at}Z`).toLocaleDateString()
                            ) : (
                              <span className="italic">Never</span>
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex gap-1 justify-end">
                              {needsReconnection && canConnect && (
                                <Button
                                  size="sm"
                                  onClick={() => handleAuthorize(connection.connection_name)}
                                  disabled={authorizeMutation.isPending}
                                >
                                  {connection.status === 'failed' ? 'Reconnect' : 'Connect'}
                                </Button>
                              )}
                              {connection.status === 'completed' && canConnect && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleAuthorize(connection.connection_name)}
                                  disabled={authorizeMutation.isPending}
                                  title="Reconnect"
                                >
                                  ↻
                                </Button>
                              )}
                              {connection.status === 'waiting_callback' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleCancel(connection.connection_name)}
                                  disabled={cancelMutation.isPending}
                                  title="Cancel"
                                >
                                  ✕
                                </Button>
                              )}
                              {connection.status === 'completed' && connection.expires_at && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  onClick={() => handleRefresh(connection.connection_name)}
                                  disabled={refreshMutation.isPending}
                                  title="Refresh token"
                                >
                                  ↻
                                </Button>
                              )}
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleEdit(connection.connection_name)}
                                title="Edit"
                              >
                                ✎
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDelete(connection.connection_name)}
                                disabled={deleteMutation.isPending}
                                title="Delete"
                                className="text-red-600 hover:text-red-700"
                              >
                                ✕
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              </div>
            )
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Link2 className="h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">
                {searchTerm ? 'No OAuth connections match your search' : 'No OAuth connections'}
              </h3>
              <p className="mt-2 text-sm text-muted-foreground max-w-md">
                {searchTerm
                  ? 'Try adjusting your search term or clear the filter'
                  : 'Get started by creating your first OAuth connection. Connect to services like Microsoft Graph, Google APIs, or any OAuth 2.0 provider.'}
              </p>
              <Button variant="outline" size="icon" onClick={handleCreate} title="Create Connection" className="mt-4">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <CreateOAuthConnectionDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        orgId={selectedOrgId || undefined}
        editConnectionName={editConnectionName}
      />

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-destructive" />
              Delete OAuth Connection
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3">
              <p>
                Are you sure you want to delete the OAuth connection <strong className="text-foreground">{connectionToDelete}</strong>?
              </p>
              <div className="bg-muted p-3 rounded-md border border-border">
                <p className="text-sm font-medium text-foreground mb-2">Before deleting:</p>
                <p className="text-sm">
                  We recommend searching for <code className="bg-background px-1.5 py-0.5 rounded text-xs">get_oauth_connection('{connectionToDelete}')</code> in your <code className="bg-background px-1.5 py-0.5 rounded text-xs">@workflows/workspace/</code> repo to confirm it isn't being used.
                </p>
              </div>
              <p className="text-sm text-destructive">
                Workflows using this connection will fail if it's deleted. This action cannot be undone.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              I'm Sure - Delete Connection
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
