/**
 * Key Vault Health Monitoring Card Component
 * Displays the health status of Azure Key Vault integration
 */

import { AlertCircle, CheckCircle2, XCircle, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { useKeyVaultHealth } from '@/hooks/useSecrets'

export function KeyVaultHealthCard() {
  const { data: healthData, isLoading, refetch, isRefetching } = useKeyVaultHealth()

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Key Vault Health</CardTitle>
          <CardDescription>Checking connection status...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!healthData) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Key Vault Health</CardTitle>
          <CardDescription>Unable to load health data</CardDescription>
        </CardHeader>
        <CardContent>
          <Button onClick={() => refetch()} size="sm" variant="outline">
            <RefreshCw className="mr-2 h-4 w-4" />
            Retry
          </Button>
        </CardContent>
      </Card>
    )
  }

  const getStatusIcon = () => {
    switch (healthData.status) {
      case 'healthy':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-500" />
    }
  }

  const getStatusBadge = () => {
    const statusColors = {
      healthy: 'default',
      degraded: 'secondary',
      unhealthy: 'destructive',
    } as const

    return (
      <Badge variant={statusColors[healthData.status]}>
        {healthData.status.toUpperCase()}
      </Badge>
    )
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              {getStatusIcon()}
              Key Vault Health
            </CardTitle>
            <CardDescription>Azure Key Vault connection status</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {getStatusBadge()}
            <Button
              onClick={() => refetch()}
              size="icon"
              variant="ghost"
              disabled={isRefetching}
            >
              <RefreshCw className={`h-4 w-4 ${isRefetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <p className="text-sm font-medium">Status Message</p>
          <p className="text-sm text-muted-foreground">{healthData.message}</p>
        </div>

        {healthData.vaultUrl && (
          <div className="space-y-2">
            <p className="text-sm font-medium">Vault URL</p>
            <p className="text-sm text-muted-foreground font-mono break-all">
              {healthData.vaultUrl}
            </p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1">
            <p className="text-sm font-medium">Can Connect</p>
            <div className="flex items-center gap-2">
              {healthData.canConnect ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm">{healthData.canConnect ? 'Yes' : 'No'}</span>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium">Can List Secrets</p>
            <div className="flex items-center gap-2">
              {healthData.canListSecrets ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm">{healthData.canListSecrets ? 'Yes' : 'No'}</span>
            </div>
          </div>

          <div className="space-y-1">
            <p className="text-sm font-medium">Can Get Secrets</p>
            <div className="flex items-center gap-2">
              {healthData.canGetSecrets ? (
                <CheckCircle2 className="h-4 w-4 text-green-500" />
              ) : (
                <XCircle className="h-4 w-4 text-red-500" />
              )}
              <span className="text-sm">{healthData.canGetSecrets ? 'Yes' : 'No'}</span>
            </div>
          </div>

          {healthData.secretCount !== undefined && healthData.secretCount !== null && (
            <div className="space-y-1">
              <p className="text-sm font-medium">Secret Count</p>
              <p className="text-sm">{healthData.secretCount}</p>
            </div>
          )}
        </div>

        <div className="pt-2 border-t">
          <p className="text-xs text-muted-foreground">
            Last checked: {formatDate(healthData.lastChecked)}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}
