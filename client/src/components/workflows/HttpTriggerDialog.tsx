import { useState } from 'react'
import { Copy, Check, Webhook, Info, ExternalLink } from 'lucide-react'
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
import type { Workflow } from '@/types/workflow'

interface HttpTriggerDialogProps {
  workflow: Workflow
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function HttpTriggerDialog({
  workflow,
  open,
  onOpenChange,
}: HttpTriggerDialogProps) {
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedCurl, setCopiedCurl] = useState(false)
  const [copiedPowerShell, setCopiedPowerShell] = useState(false)

  // Get base URL for direct function access
  const functionAppUrl = import.meta.env['VITE_WORKFLOW_FUNCTION_URL'] || 'https://{your-function-app}.azurewebsites.net'
  const directUrl = `${functionAppUrl}/api/workflows/${workflow.name}`

  const copyToClipboard = async (text: string, setCopied: (value: boolean) => void) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  // Example parameters
  const exampleParams = workflow.parameters?.reduce((acc, param) => ({
    ...acc,
    [param.name ?? 'param']: param.defaultValue || (param.type === 'string' ? '<string>' : param.type === 'int' ? 0 : param.type === 'bool' ? false : null),
  }), {} as Record<string, any>) ?? {}

  // cURL example
  const curlExample = `curl -X POST "${directUrl}" \\
  -H "Content-Type: application/json" \\
  -H "x-functions-key: YOUR_FUNCTION_KEY" \\
  ${false ? `-H "X-Organization-Id: YOUR_ORG_ID" \\\n  ` : ''}-d '${JSON.stringify(exampleParams, null, 2)}'`

  // PowerShell example
  const powerShellExample = `$headers = @{
    "Content-Type" = "application/json"
    "x-functions-key" = "YOUR_FUNCTION_KEY"${false ? '\n    "X-Organization-Id" = "YOUR_ORG_ID"' : ''}
}

$body = @${JSON.stringify(exampleParams, null, 4).replace(/{/g, '{').replace(/}/g, '}')}

Invoke-RestMethod -Uri "${directUrl}" \`
    -Method POST \`
    -Headers $headers \`
    -Body ($body | ConvertTo-Json)`

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="!max-w-fit max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Webhook className="h-5 w-5" />
            HTTP Trigger Configuration
          </DialogTitle>
          <DialogDescription>
            Call <span className="font-mono font-semibold">{workflow.name}</span> via HTTP
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Info Alert */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-sm">
              This workflow can be called from external systems using an Azure Function key for authentication.
              {false && ' Organization ID is required for this workflow.'}
            </AlertDescription>
          </Alert>

          {/* Direct Function URL */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Direct Function URL</label>
            <div className="flex items-center gap-2">
              <div className="flex-1 p-3 bg-muted rounded-md font-mono text-sm overflow-x-auto">
                {directUrl}
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => copyToClipboard(directUrl, setCopiedUrl)}
              >
                {copiedUrl ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Use <code className="px-1 py-0.5 bg-muted rounded">x-functions-key</code> header for authentication
            </p>
          </div>

          {/* Function Key Instructions */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Azure Function Key</label>
            <div className="p-4 bg-muted rounded-md space-y-2 text-sm">
              <p><strong>To get your function key:</strong></p>
              <ol className="list-decimal list-inside space-y-1 ml-2">
                <li>Go to Azure Portal → Your Function App</li>
                <li>Navigate to "Functions" → Select your workflow function</li>
                <li>Click "Function Keys" → Copy the default key</li>
              </ol>
              <p className="flex items-center gap-2 mt-2">
                <ExternalLink className="h-3 w-3" />
                <a
                  href="https://learn.microsoft.com/en-us/azure/azure-functions/functions-bindings-http-webhook-trigger?tabs=python-v2%2Cisolated-process%2Cnodejs-v4%2Cfunctionsv2&pivots=programming-language-python#authorization-keys"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:underline"
                >
                  Learn more about Azure Function keys
                </a>
              </p>
            </div>
          </div>

          {/* Required Headers */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Required Headers</label>
            <div className="space-y-1 text-sm">
              <div className="flex items-center gap-2">
                <Badge variant="outline">Content-Type</Badge>
                <span className="text-muted-foreground">application/json</span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="outline">x-functions-key</Badge>
                <span className="text-muted-foreground">Your Azure Function key</span>
              </div>
              {false && (
                <div className="flex items-center gap-2">
                  <Badge variant="outline">X-Organization-Id</Badge>
                  <span className="text-muted-foreground">Your organization UUID</span>
                </div>
              )}
            </div>
          </div>

          {/* Body Format */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Request Body (Flat JSON)</label>
            <div className="p-4 bg-muted rounded-md">
              <pre className="text-xs overflow-x-auto">
                <code>{JSON.stringify(exampleParams, null, 2)}</code>
              </pre>
            </div>
            <p className="text-xs text-muted-foreground">
              Send workflow parameters as flat JSON (no nested "inputData" or "parameters" object)
            </p>
          </div>

          {/* cURL Example */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Example: cURL</label>
            <div className="relative">
              <pre className="p-4 bg-muted rounded-md text-xs overflow-x-auto">
                <code>{curlExample}</code>
              </pre>
              <Button
                variant="ghost"
                size="sm"
                className="absolute top-2 right-2"
                onClick={() => copyToClipboard(curlExample, setCopiedCurl)}
              >
                {copiedCurl ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              </Button>
            </div>
          </div>

          {/* PowerShell Example */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Example: PowerShell</label>
            <div className="relative">
              <pre className="p-4 bg-muted rounded-md text-xs overflow-x-auto">
                <code>{powerShellExample}</code>
              </pre>
              <Button
                variant="ghost"
                size="sm"
                className="absolute top-2 right-2"
                onClick={() => copyToClipboard(powerShellExample, setCopiedPowerShell)}
              >
                {copiedPowerShell ? <Check className="h-3 w-3" /> : <Copy className="h-3 w-3" />}
              </Button>
            </div>
          </div>

          {/* Usage Notes */}
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription className="text-xs space-y-1">
              <p><strong>UI vs. External Calls:</strong></p>
              <ul className="list-disc list-inside ml-2 space-y-1">
                <li><strong>Via UI/Forms:</strong> Authenticated with Azure AD (no function key needed)</li>
                <li><strong>Direct HTTP:</strong> Requires Azure Function key in x-functions-key header</li>
              </ul>
            </AlertDescription>
          </Alert>
        </div>
      </DialogContent>
    </Dialog>
  )
}
