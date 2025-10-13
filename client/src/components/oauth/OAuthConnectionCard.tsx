import { Trash2, ExternalLink, Clock, CheckCircle2, XCircle, Loader2, AlertCircle, Copy, Check, Pencil, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { toast } from 'sonner'
import type { OAuthConnectionSummary } from '@/types/oauth'
import { getStatusColor, getStatusLabel, isExpired, expiresSoon } from '@/types/oauth'

interface OAuthConnectionCardProps {
  connection: OAuthConnectionSummary
  onAuthorize: (connectionName: string) => Promise<string | void>
  onEdit: (connectionName: string) => void
  onRefresh: (connectionName: string) => void
  onDelete: (connectionName: string) => void
  onCancel?: (connectionName: string) => void
  isAuthorizing?: boolean
  isRefreshing?: boolean
  isDeleting?: boolean
  isCanceling?: boolean
}

export function OAuthConnectionCard({
  connection,
  onAuthorize,
  onEdit,
  onRefresh,
  onDelete,
  onCancel,
  isAuthorizing = false,
  isRefreshing = false,
  isDeleting = false,
  isCanceling = false,
}: OAuthConnectionCardProps) {
  const [copiedCallback, setCopiedCallback] = useState(false)

  const callbackUrl = `${window.location.origin}/oauth/callback/${connection.connection_name}`

  const handleCopyCallback = () => {
    navigator.clipboard.writeText(callbackUrl)
    setCopiedCallback(true)
    toast.success('Callback URL copied to clipboard')
    setTimeout(() => setCopiedCallback(false), 2000)
  }

  const handleAuthorizeClick = async () => {
    await onAuthorize(connection.connection_name)
  }

  const getStatusIcon = () => {
    switch (connection.status) {
      case 'completed':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />
      case 'waiting_callback':
      case 'testing':
        return <Loader2 className="h-5 w-5 text-yellow-500 animate-spin" />
      default:
        return <Clock className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusBadgeVariant = (): "default" | "destructive" | "secondary" | "outline" | "success" => {
    const color = getStatusColor(connection.status)
    switch (color) {
      case 'green':
        return 'default' // This will show as green for completed status
      case 'red':
        return 'destructive'
      case 'yellow':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  const getStatusBadgeClassName = () => {
    const color = getStatusColor(connection.status)
    if (color === 'green') {
      return 'bg-green-500 hover:bg-green-600 text-white border-green-500'
    }
    return ''
  }

  const canConnect = connection.oauth_flow_type !== 'client_credentials'
  const needsReconnection =
    connection.status === 'not_connected' || connection.status === 'failed'

  const expirationWarning = connection.expires_at && expiresSoon(connection.expires_at)
  const isTokenExpired = connection.expires_at && isExpired(connection.expires_at)

  const formatDateTime = (dateStr?: string) => {
    if (!dateStr) return 'Never'

    // Parse the date - backend sends UTC timestamps without 'Z' suffix
    // Add 'Z' to explicitly mark it as UTC, then JavaScript will convert to local time
    const utcDateStr = dateStr.endsWith('Z') ? dateStr : `${dateStr}Z`
    const date = new Date(utcDateStr)
    const now = new Date()
    const diffMs = date.getTime() - now.getTime()
    const diffMins = Math.floor(Math.abs(diffMs) / 60000)
    const diffHours = Math.floor(Math.abs(diffMs) / 3600000)
    const diffDays = Math.floor(Math.abs(diffMs) / 86400000)

    // For dates within 7 days, show relative time
    if (diffDays < 7) {
      // Past dates (negative diffMs) - show "X ago"
      if (diffMs < 0) {
        if (diffMins < 60) {
          return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`
        } else if (diffHours < 24) {
          return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`
        } else {
          return `${diffDays} day${diffDays !== 1 ? 's' : ''} ago`
        }
      }

      // Future dates (positive diffMs) - show "in X"
      if (diffMs > 0) {
        if (diffMins < 60) {
          return `in ${diffMins} minute${diffMins !== 1 ? 's' : ''}`
        } else if (diffHours < 24) {
          return `in ${diffHours} hour${diffHours !== 1 ? 's' : ''}`
        } else {
          return `in ${diffDays} day${diffDays !== 1 ? 's' : ''}`
        }
      }

      // Exactly now
      return 'just now'
    }

    // Absolute dates for far past/future (converts to user's local timezone)
    return date.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  return (
    <Card className="flex flex-col h-full hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-2">
            {getStatusIcon()}
            <div>
              <CardTitle className="text-lg">{connection.connection_name}</CardTitle>
              <CardDescription className="text-xs mt-1">
                {connection.oauth_flow_type.replace('_', ' ')}
              </CardDescription>
            </div>
          </div>
          <Badge variant={getStatusBadgeVariant()} className={getStatusBadgeClassName()}>
            {getStatusLabel(connection.status)}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="flex-1 space-y-3">
        {/* Callback URL for not connected state */}
        {needsReconnection && canConnect && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Callback URL:</p>
            <div className="flex items-center gap-2">
              <code className="flex-1 px-2 py-1 bg-muted rounded text-xs break-all">
                {callbackUrl}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleCopyCallback}
              >
                {copiedCallback ? (
                  <Check className="h-3 w-3" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Add this URL to your OAuth app's allowed redirect URIs
            </p>
          </div>
        )}

        {/* Status Message - only show for non-completed statuses */}
        {connection.status_message && connection.status !== 'completed' && (
          <div className="text-sm text-muted-foreground bg-muted p-2 rounded-md">
            {connection.status_message}
          </div>
        )}

        {/* Expiration Warning */}
        {connection.status === 'completed' && isTokenExpired && (
          <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 p-2 rounded-md">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <span>Token expired. Reconnect to continue using this connection.</span>
          </div>
        )}

        {connection.status === 'completed' && !isTokenExpired && expirationWarning && (
          <div className="flex items-start gap-2 text-sm text-yellow-600 bg-yellow-50 p-2 rounded-md">
            <AlertCircle className="h-4 w-4 mt-0.5" />
            <span>Token expires soon</span>
          </div>
        )}

        {/* Metadata Badges */}
        <div className="grid grid-cols-2 gap-2">
          <Badge variant="outline" className="text-xs justify-center w-full">
            <Clock className="mr-1 h-3 w-3" />
            Created {formatDateTime(connection.created_at)}
          </Badge>

          {connection.expires_at && (
            <Badge
              variant={isTokenExpired ? "destructive" : expirationWarning ? "secondary" : "default"}
              className="text-xs justify-center w-full"
            >
              {isTokenExpired ? (
                <>
                  <XCircle className="mr-1 h-3 w-3" />
                  Expired {formatDateTime(connection.expires_at)}
                </>
              ) : (
                <>
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Expires {formatDateTime(connection.expires_at)}
                </>
              )}
            </Badge>
          )}

          {connection.last_refresh_at && (
            <Badge variant="outline" className="text-xs justify-center w-full col-span-2">
              <RefreshCw className="mr-1 h-3 w-3" />
              Refreshed {formatDateTime(connection.last_refresh_at)}
            </Badge>
          )}
        </div>
      </CardContent>

      <CardFooter className="flex flex-col gap-2">
        <div className="flex gap-2 w-full">
          {needsReconnection && canConnect && (
            <Button
              onClick={handleAuthorizeClick}
              disabled={isAuthorizing}
              className="flex-1"
            >
              {isAuthorizing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Connecting...
                </>
              ) : (
                <>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  {connection.status === 'failed' ? 'Reconnect' : 'Connect'}
                </>
              )}
            </Button>
          )}

          {connection.status === 'completed' && canConnect && (
            <Button
              onClick={handleAuthorizeClick}
              disabled={isAuthorizing}
              variant="outline"
              className="flex-1"
            >
              {isAuthorizing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Reconnecting...
                </>
              ) : (
                <>
                  <ExternalLink className="mr-2 h-4 w-4" />
                  Reconnect
                </>
              )}
            </Button>
          )}

          {connection.status === 'waiting_callback' && (
            <>
              <Button variant="outline" className="flex-1" disabled>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Connecting...
              </Button>
              {onCancel && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onCancel(connection.connection_name)}
                  disabled={isCanceling}
                >
                  {isCanceling ? 'Canceling...' : 'Cancel'}
                </Button>
              )}
            </>
          )}

          {connection.status === 'testing' && (
            <Button variant="outline" className="flex-1" disabled>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Testing connection...
            </Button>
          )}

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onRefresh(connection.connection_name)}
                  disabled={isRefreshing || connection.status !== 'completed' || !connection.expires_at}
                >
                  <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Refresh access token</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onEdit(connection.connection_name)}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Edit connection</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>

          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="outline"
                  size="icon"
                  onClick={() => onDelete(connection.connection_name)}
                  disabled={isDeleting}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Delete connection</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
      </CardFooter>
    </Card>
  )
}
