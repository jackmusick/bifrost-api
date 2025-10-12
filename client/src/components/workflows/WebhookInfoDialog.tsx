import { useState, useEffect } from 'react'
import { Copy, Check, Webhook, Lock, Info, RefreshCw, AlertTriangle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { workflowKeysService, type WorkflowKey } from '@/services/workflowKeys'
import type { Workflow } from '@/types/workflow'

interface WebhookInfoDialogProps {
  workflow: Workflow
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function WebhookInfoDialog({
  workflow,
  open,
  onOpenChange,
}: WebhookInfoDialogProps) {
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedKey, setCopiedKey] = useState(false)
  const [workflowKeyData, setWorkflowKeyData] = useState<WorkflowKey | null>(null)
  const [isLoadingKey, setIsLoadingKey] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [keyError, setKeyError] = useState<string | null>(null)

  // Get base URL (from environment or current location)
  const baseUrl = import.meta.env['VITE_API_URL'] || window.location.origin
  const webhookUrl = `${baseUrl}/api/workflows/execute`

  // Always use org scope if org available
  const orgId = sessionStorage.getItem('current_org_id') || undefined
  const scope: 'global' | 'org' = orgId ? 'org' : 'global'

  // Fetch workflow key when dialog opens
  useEffect(() => {
    if (open) {
      fetchWorkflowKey()
    }
  }, [open])

  const fetchWorkflowKey = async () => {
    setIsLoadingKey(true)
    setKeyError(null)
    try {
      const keyData = await workflowKeysService.getWorkflowKey(scope, orgId)
      setWorkflowKeyData(keyData)
    } catch (error: any) {
      if (error.statusCode === 404) {
        setKeyError('No workflow key generated yet. Click "Generate Key" to create one.')
      } else {
        setKeyError(error.message || 'Failed to fetch workflow key')
      }
    } finally {
      setIsLoadingKey(false)
    }
  }

  const handleGenerateKey = async () => {
    setIsGenerating(true)
    setKeyError(null)
    try {
      const newKey = await workflowKeysService.generateWorkflowKey(scope, orgId)
      setWorkflowKeyData(newKey)
    } catch (error: any) {
      setKeyError(error.message || 'Failed to generate workflow key')
    } finally {
      setIsGenerating(false)
    }
  }

  const copyToClipboard = async (text: string, setCopied: (value: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const curlExample = workflowKeyData ? `curl -X POST ${webhookUrl} \\
  -H "Content-Type: application/json" \\
  ${false ? `-H "X-Organization-Id: ${orgId || 'YOUR_ORG_ID'}" \\
  ` : ''}-H "X-Workflow-Key: ${workflowKeyData.key}" \\
  -d '{
    "workflowName": "${workflow.name}",
    "inputData": ${JSON.stringify(
      workflow.parameters?.reduce((acc, param) => ({
        ...acc,
        [param.name ?? 'param']: param.defaultValue || `<${param.type}>`,
      }), {} as Record<string, any>) ?? {},
      null,
      4
    ).split('\n').join('\n    ')}
  }'` : 'Generate a workflow key first to see the example cURL command'

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            HTTP Trigger Configuration
            <Badge variant="secondary" className="ml-auto font-normal">
              {scope === 'global' ? 'Global' : 'Org-specific'}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Trigger <span className="font-mono font-semibold">{workflow.name}</span> via HTTP POST
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Security Notice */}
          <Alert>
            <Lock className="h-4 w-4" />
            <AlertDescription>
              This workflow requires the <strong>X-Workflow-Key</strong> header for authentication
            </AlertDescription>
          </Alert>

          {/* Endpoint URL */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Webhook URL</label>
            <div className="flex items-center gap-2">
              <div className="flex-1 p-3 bg-muted rounded-md font-mono text-sm overflow-x-auto">
                {webhookUrl}
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => copyToClipboard(webhookUrl, setCopiedUrl)}
              >
                {copiedUrl ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
          </div>

          {/* Workflow Key */}
          <div className="space-y-2">
            <label className="text-sm font-medium flex items-center justify-between">
              <span className="flex items-center gap-2">
                Workflow Key
                <Badge variant="secondary" className="font-normal">
                  X-Workflow-Key
                </Badge>
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerateKey}
                disabled={isGenerating || isLoadingKey}
              >
                <RefreshCw className={`mr-2 h-3 w-3 ${isGenerating ? 'animate-spin' : ''}`} />
                {workflowKeyData ? 'Regenerate Key' : 'Generate Key'}
              </Button>
            </label>

            {isLoadingKey ? (
              <div className="flex items-center justify-center p-6 bg-muted rounded-md">
                <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                <span className="text-sm text-muted-foreground">Loading workflow key...</span>
              </div>
            ) : keyError ? (
              <Alert variant="destructive">
                <AlertTriangle className="h-4 w-4" />
                <AlertDescription className="text-sm">{keyError}</AlertDescription>
              </Alert>
            ) : workflowKeyData ? (
              <>
                <div className="flex items-center gap-2">
                  <div className="flex-1 p-3 bg-muted rounded-md font-mono text-sm overflow-x-auto">
                    {workflowKeyData.key}
                  </div>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={() => copyToClipboard(workflowKeyData.key, setCopiedKey)}
                  >
                    {copiedKey ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  {workflowKeyData.message || 'Keep this key secure! It acts as authentication for webhook requests.'}
                </p>
                {workflowKeyData.lastUsedAt && (
                  <p className="text-xs text-muted-foreground">
                    Last used: {new Date(workflowKeyData.lastUsedAt).toLocaleString()}
                  </p>
                )}
              </>
            ) : null}
          </div>

          {/* Required Headers */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Required Headers</label>
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant="outline">Content-Type</Badge>
                <span className="text-muted-foreground">application/json</span>
              </div>
              {orgId && (
                <div className="flex items-center gap-2">
                  <Badge variant="outline">X-Organization-Id</Badge>
                  <span className="text-muted-foreground">
                    {orgId}
                  </span>
                </div>
              )}
              <div className="flex items-center gap-2">
                <Badge variant="outline">X-Workflow-Key</Badge>
                <span className="text-muted-foreground">Workflow authentication key</span>
              </div>
            </div>
          </div>

          {/* Example cURL Command */}
          {workflowKeyData && (
            <div className="space-y-2">
              <label className="text-sm font-medium">Example cURL Command</label>
              <div className="relative">
                <pre className="p-4 bg-muted rounded-md text-xs overflow-x-auto">
                  <code>{curlExample}</code>
                </pre>
                <Button
                  variant="ghost"
                  size="sm"
                  className="absolute top-2 right-2"
                  onClick={() => copyToClipboard(curlExample, () => {})}
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            </div>
          )}

          {/* Usage Notes */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs space-y-1">
              <p><strong>Scope:</strong> This workflow uses a <strong>{scope === 'global' ? 'GLOBAL' : 'org-specific'}</strong> workflow key.</p>
              {scope === 'global' ? (
                <p>Global workflows can be triggered without org context and use the MSP-wide workflow key.</p>
              ) : (
                <p>Org-specific workflows require X-Organization-Id header and use org-specific keys with fallback to global.</p>
              )}
            </AlertDescription>
          </Alert>
        </div>
      </DialogContent>
    </Dialog>
  )
}
