import { useEffect, useState, useRef } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { oauthService } from '@/services/oauth'

export function OAuthCallback() {
  const navigate = useNavigate()
  const { connectionName } = useParams<{ connectionName: string }>()
  const [searchParams] = useSearchParams()
  const [status, setStatus] = useState<'processing' | 'success' | 'error'>('processing')
  const [message, setMessage] = useState('Processing OAuth callback...')
  const [warning, setWarning] = useState<string | null>(null)
  const hasProcessed = useRef(false)

  useEffect(() => {
    const handleCallback = async () => {
      // Prevent double-processing (React.StrictMode, refresh, etc.)
      if (hasProcessed.current) {
        return
      }
      hasProcessed.current = true
      if (!connectionName) {
        setStatus('error')
        setMessage('Missing connection name in URL')
        return
      }

      // Get query parameters from OAuth provider
      const code = searchParams.get('code')
      const error = searchParams.get('error')
      const errorDescription = searchParams.get('error_description')
      const state = searchParams.get('state')

      // Check for error from OAuth provider
      if (error) {
        setStatus('error')
        setMessage(`OAuth authorization failed: ${errorDescription || error}`)
        return
      }

      // Check for authorization code
      if (!code) {
        setStatus('error')
        setMessage('Missing authorization code from OAuth provider')
        return
      }

      try {
        // Send the authorization code to the API for token exchange
        const response = await oauthService.handleCallback(connectionName, code, state)

        setStatus('success')
        setMessage('OAuth connection completed successfully!')

        // Check for warning (e.g., missing refresh token)
        if (response && typeof response === 'object' && 'warning' in response && response.warning) {
          setWarning(response.warning as string)
        }

        // Notify parent window to refresh connections IMMEDIATELY
        if (window.opener) {
          window.opener.postMessage({
            type: 'oauth_success',
            connectionName
          }, window.location.origin)
        }

        // Brief delay to show success message (longer if there's a warning), then close
        const delay = warning ? 5000 : 1500
        setTimeout(() => {
          window.close()
          // Fallback: If window.close() fails (not a popup), navigate to oauth page
          setTimeout(() => {
            navigate('/oauth')
          }, 100)
        }, delay)
      } catch (err: unknown) {
        setStatus('error')
        const errorMsg = (err as Error).message || 'Failed to complete OAuth connection'

        // Provide helpful message for common errors
        if (errorMsg.includes('already been redeemed') || errorMsg.includes('already been used')) {
          setMessage('This authorization has already been processed. You can close this window.')
          // Auto-close since this is likely a refresh/duplicate
          setTimeout(() => {
            window.close()
          }, 2000)
        } else {
          setMessage(errorMsg)
        }
      }
    }

    handleCallback()
  }, [connectionName, searchParams, navigate, warning])

  return (
    <div className="flex items-center justify-center min-h-screen bg-background p-4">
      <Card className="max-w-md w-full">
        <CardHeader>
          <div className="flex items-center gap-2">
            {status === 'processing' && <Loader2 className="h-6 w-6 animate-spin text-blue-500" />}
            {status === 'success' && <CheckCircle2 className="h-6 w-6 text-green-500" />}
            {status === 'error' && <XCircle className="h-6 w-6 text-red-500" />}
            <CardTitle>
              {status === 'processing' && 'Processing OAuth Callback'}
              {status === 'success' && 'Authorization Successful'}
              {status === 'error' && 'Authorization Failed'}
            </CardTitle>
          </div>
          <CardDescription>
            Connection: <code className="font-mono">{connectionName}</code>
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">{message}</p>

          {status === 'success' && warning && (
            <Alert className="mb-4 border-yellow-500 bg-yellow-50">
              <AlertTriangle className="h-4 w-4 text-yellow-600" />
              <AlertDescription className="text-sm text-yellow-800">
                {warning}
              </AlertDescription>
            </Alert>
          )}

          {status === 'success' && (
            <p className="text-xs text-muted-foreground">
              This window will close automatically...
            </p>
          )}

          {status === 'error' && (
            <Button onClick={() => window.close()} variant="outline" className="w-full">
              Close
            </Button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
