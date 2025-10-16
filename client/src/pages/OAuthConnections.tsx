import { useState, useEffect } from 'react'
import { Link2, Plus, RefreshCw, AlertTriangle } from 'lucide-react'
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
import { Skeleton } from '@/components/ui/skeleton'
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


export function OAuthConnections() {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editConnectionName, setEditConnectionName] = useState<string | undefined>(undefined)
  const [selectedOrgId] = useState<string | undefined>(undefined)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [connectionToDelete, setConnectionToDelete] = useState<string | null>(null)

  const { data: connections, isLoading, refetch } = useOAuthConnections()
  const deleteMutation = useDeleteOAuthConnection()
  const authorizeMutation = useAuthorizeOAuthConnection()
  const cancelMutation = useCancelOAuthAuthorization()
  const refreshMutation = useRefreshOAuthToken()

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
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-6">
      <div className="flex-shrink-0">
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
            <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button onClick={handleCreate}>
              <Plus className="mr-2 h-4 w-4" />
              New Connection
            </Button>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 flex-shrink-0">
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
      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Your Connections</CardTitle>
              <CardDescription>
                {connections && connections.length > 0
                  ? `Showing ${connections.length} OAuth connection${connections.length !== 1 ? 's' : ''}`
                  : 'No connections configured yet'}
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col">
          {isLoading ? (
            <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <Skeleton key={i} className="h-48 w-full" />
              ))}
            </div>
          ) : connections && connections.length > 0 ? (
            <div className="overflow-auto max-h-full">
              <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4 pb-4">
                {connections.map((connection) => (
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
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Link2 className="h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No OAuth connections</h3>
              <p className="mt-2 text-sm text-muted-foreground max-w-md">
                Get started by creating your first OAuth connection. Connect to services like
                Microsoft Graph, Google APIs, or any OAuth 2.0 provider.
              </p>
              <Button onClick={handleCreate} className="mt-4">
                <Plus className="mr-2 h-4 w-4" />
                Create Connection
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
