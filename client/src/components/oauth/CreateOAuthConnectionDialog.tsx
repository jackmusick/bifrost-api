import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Info, Sparkles, Copy, Check } from 'lucide-react'
import { useCreateOAuthConnection, useUpdateOAuthConnection, useOAuthConnection } from '@/hooks/useOAuth'
import type { components } from '@/lib/v1'
import { OAuthProviderPreset, OAUTH_PROVIDER_PRESETS } from '@/lib/client-types'
type CreateOAuthConnectionRequest = components['schemas']['CreateOAuthConnectionRequest']
type OAuthConnectionDetail = components['schemas']['OAuthConnectionDetail']
type OAuthFlowType = OAuthProviderPreset['oauth_flow_type']
import { toast } from 'sonner'
import { useEffect } from 'react'

interface CreateOAuthConnectionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  orgId?: string | undefined
  editConnectionName?: string | undefined
}

export function CreateOAuthConnectionDialog({
  open,
  onOpenChange,
  editConnectionName,
}: CreateOAuthConnectionDialogProps) {
  const [step, setStep] = useState<1 | 2>(1)
  const [mode, setMode] = useState<'preset' | 'custom'>('preset')
  const [selectedPreset, setSelectedPreset] = useState<string>('')
  const [copiedRedirect, setCopiedRedirect] = useState(false)
  const [formData, setFormData] = useState<CreateOAuthConnectionRequest>({
    connection_name: '',
    description: '',
    oauth_flow_type: 'authorization_code',
    client_id: '',
    client_secret: '',
    authorization_url: '',
    token_url: '',
    scopes: '',
  })

  const isEditMode = !!editConnectionName
  const createMutation = useCreateOAuthConnection()
  const updateMutation = useUpdateOAuthConnection()
  const { data: existingConnection } = useOAuthConnection(editConnectionName || '') as { data?: OAuthConnectionDetail | undefined }

  // Load existing connection data when in edit mode
  useEffect(() => {
    if (isEditMode && existingConnection && open) {
      setFormData({
        connection_name: existingConnection.connection_name,
        description: existingConnection.description || '',
        oauth_flow_type: existingConnection.oauth_flow_type,
        client_id: existingConnection.client_id,
        client_secret: '', // Don't populate for security
        authorization_url: existingConnection.authorization_url,
        token_url: existingConnection.token_url,
        scopes: existingConnection.scopes || '',
      })
      setStep(2) // Skip to step 2 in edit mode
    } else if (!open) {
      // Reset when dialog closes
      setFormData({
        connection_name: '',
        description: '',
        oauth_flow_type: 'authorization_code',
        client_id: '',
        client_secret: '',
        authorization_url: '',
        token_url: '',
        scopes: '',
      })
      setStep(1)
      setSelectedPreset('')
    }
  }, [isEditMode, existingConnection, open])

  const redirectUri = formData.connection_name
    ? `${window.location.origin}/oauth/callback/${formData.connection_name}`
    : ''

  const handlePresetSelect = (presetName: string) => {
    setSelectedPreset(presetName)
    const preset = OAUTH_PROVIDER_PRESETS[presetName]
    if (preset) {
      setFormData({
        ...formData,
        oauth_flow_type: preset.oauth_flow_type,
        authorization_url: preset.authorization_url,
        token_url: preset.token_url,
        scopes: preset.default_scopes,
      })
    }
  }

  const handleCopyRedirectUri = () => {
    navigator.clipboard.writeText(redirectUri)
    setCopiedRedirect(true)
    toast.success('Redirect URI copied to clipboard')
    setTimeout(() => setCopiedRedirect(false), 2000)
  }

  const handleStep1Next = () => {
    if (!formData.connection_name) {
      toast.error('Connection name is required')
      return
    }
    setStep(2)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (isEditMode) {
      // Update existing connection
      const updateData: Record<string, string | null> = {
        client_id: formData.client_id,
        authorization_url: formData.authorization_url,
        token_url: formData.token_url,
        scopes: formData.scopes,
      }

      // Only include client_secret if provided
      if (formData.client_secret) {
        (updateData as Record<string, string | null>)['client_secret'] = formData.client_secret
      }

      await updateMutation.mutateAsync({
        connectionName: formData.connection_name,
        data: updateData as Record<string, string | null>,
      })
    } else {
      // Create new connection
      await createMutation.mutateAsync(formData)
    }

    // Reset form and close
    setStep(1)
    setFormData({
      connection_name: '',
      description: '',
      oauth_flow_type: 'authorization_code',
      client_id: '',
      client_secret: '',
      authorization_url: '',
      token_url: '',
      scopes: '',
    })
    setSelectedPreset('')
    onOpenChange(false)
  }

  const isStep2Valid = () => {
    return (
      formData.client_id &&
      formData.authorization_url &&
      formData.token_url
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>
              {isEditMode
                ? `Edit OAuth Connection: ${editConnectionName}`
                : step === 1
                  ? 'Create OAuth Connection - Step 1'
                  : 'Create OAuth Connection - Step 2'}
            </DialogTitle>
            <DialogDescription>
              {isEditMode
                ? 'Update OAuth 2.0 connection details'
                : step === 1
                  ? 'Start by naming your connection to get the redirect URI'
                  : 'Configure OAuth 2.0 connection details'}
            </DialogDescription>
          </DialogHeader>

          {step === 1 && !isEditMode ? (
            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="connection_name">Connection Name *</Label>
                <Input
                  id="connection_name"
                  value={formData.connection_name}
                  onChange={(e) =>
                    setFormData({ ...formData, connection_name: e.target.value })
                  }
                  placeholder="microsoft_graph"
                  pattern="[a-zA-Z0-9_-]+"
                  title="Only alphanumeric characters, hyphens, and underscores allowed"
                  required
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  Unique identifier for this connection. Use in workflows like{' '}
                  <code className="px-1 bg-muted rounded">get_oauth_connection(context, "{formData.connection_name || 'name'}")</code>
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description (Optional)</Label>
                <Textarea
                  id="description"
                  value={formData.description || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="OAuth connection for Microsoft Graph API integration"
                  rows={2}
                />
                <p className="text-xs text-muted-foreground">
                  Brief description of what this connection is used for
                </p>
              </div>

              {formData.connection_name && (
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-2">
                      <p className="font-semibold text-sm">Your Redirect URI:</p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 px-2 py-1 bg-muted rounded text-xs break-all">
                          {redirectUri}
                        </code>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleCopyRedirectUri}
                        >
                          {copiedRedirect ? (
                            <Check className="h-4 w-4" />
                          ) : (
                            <Copy className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Copy this and add it to your OAuth app's allowed redirect URIs before continuing
                      </p>
                    </div>
                  </AlertDescription>
                </Alert>
              )}
            </div>
          ) : (
            <div className="space-y-4 mt-4">
              <Tabs value={mode} onValueChange={(v) => setMode(v as 'preset' | 'custom')}>
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="preset">
                    <Sparkles className="mr-2 h-4 w-4" />
                    Quick Start (Presets)
                  </TabsTrigger>
                  <TabsTrigger value="custom">Custom Provider</TabsTrigger>
                </TabsList>

                <TabsContent value="preset" className="space-y-4">
                  <div className="space-y-2">
                    <Label>Select Provider</Label>
                    <Select value={selectedPreset} onValueChange={handlePresetSelect}>
                      <SelectTrigger>
                        <SelectValue placeholder="Choose a provider..." />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(OAUTH_PROVIDER_PRESETS).map(([key, preset]) => (
                          <SelectItem key={key} value={key}>
                            <div className="flex items-center gap-2">
                              <span>{preset.icon}</span>
                              <span>{preset.displayName}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {selectedPreset && OAUTH_PROVIDER_PRESETS[selectedPreset] && (
                      <Alert>
                        <Info className="h-4 w-4" />
                        <AlertDescription className="text-xs">
                          <a
                            href={OAUTH_PROVIDER_PRESETS[selectedPreset].documentation_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:underline"
                          >
                            View {OAUTH_PROVIDER_PRESETS[selectedPreset].displayName} documentation →
                          </a>
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="custom" className="space-y-4">
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription className="text-xs">
                      Configure a custom OAuth 2.0 provider. You'll need the authorization and token
                      URLs from the provider's documentation.
                    </AlertDescription>
                  </Alert>
                </TabsContent>
              </Tabs>

              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="oauth_flow_type">OAuth Flow Type *</Label>
                  <Select
                    value={formData.oauth_flow_type}
                    onValueChange={(value) =>
                      setFormData({ ...formData, oauth_flow_type: value as OAuthFlowType })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="authorization_code">
                        Authorization Code (Interactive)
                      </SelectItem>
                      <SelectItem value="client_credentials">
                        Client Credentials (Service-to-Service)
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    {formData.oauth_flow_type === 'authorization_code'
                      ? 'Requires user authorization. Use for delegated permissions.'
                      : 'No user authorization required. Use for application permissions.'}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="client_id">Client ID *</Label>
                    <Input
                      id="client_id"
                      value={formData.client_id}
                      onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
                      placeholder="abc123..."
                      required
                      className="font-mono"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="client_secret">Client Secret</Label>
                    <Input
                      id="client_secret"
                      type="password"
                      value={formData.client_secret || ''}
                      onChange={(e) =>
                        setFormData({ ...formData, client_secret: e.target.value })
                      }
                      placeholder={isEditMode ? "Leave empty to keep existing..." : "Optional for PKCE flow..."}
                    />
                    <p className="text-xs text-muted-foreground">
                      {isEditMode
                        ? "Leave empty to keep the existing secret, or enter a new one to update"
                        : "Optional: Leave empty for PKCE (Proof Key for Code Exchange) flow"}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="authorization_url">Authorization URL *</Label>
                  <Input
                    id="authorization_url"
                    value={formData.authorization_url}
                    onChange={(e) =>
                      setFormData({ ...formData, authorization_url: e.target.value })
                    }
                    placeholder="https://provider.com/oauth/authorize"
                    pattern="https://.*"
                    required
                    className="font-mono text-xs"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="token_url">Token URL *</Label>
                  <Input
                    id="token_url"
                    value={formData.token_url}
                    onChange={(e) => setFormData({ ...formData, token_url: e.target.value })}
                    placeholder="https://provider.com/oauth/token"
                    pattern="https://.*"
                    required
                    className="font-mono text-xs"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="scopes">Scopes (comma or space separated)</Label>
                  <Textarea
                    id="scopes"
                    value={formData.scopes}
                    onChange={(e) => setFormData({ ...formData, scopes: e.target.value })}
                    placeholder="read,write or https://graph.microsoft.com/.default"
                    rows={2}
                    className="font-mono text-xs"
                  />
                  <p className="text-xs text-muted-foreground">
                    OAuth permissions to request. Leave empty for default scopes.
                  </p>
                </div>
              </div>
            </div>
          )}

          <DialogFooter className="mt-6">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                if (step === 2) {
                  setStep(1)
                } else {
                  onOpenChange(false)
                }
              }}
              disabled={createMutation.isPending}
            >
              {step === 2 ? 'Back' : 'Cancel'}
            </Button>
            {step === 1 ? (
              <Button
                type="button"
                onClick={handleStep1Next}
                disabled={!formData.connection_name}
              >
                Next: Configure OAuth
              </Button>
            ) : (
              <Button type="submit" disabled={!isStep2Valid() || createMutation.isPending || updateMutation.isPending}>
                {isEditMode
                  ? (updateMutation.isPending ? 'Updating...' : 'Update Connection')
                  : (createMutation.isPending ? 'Creating...' : 'Create Connection')}
              </Button>
            )}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
