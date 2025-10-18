import { useState } from 'react'
import { Key, Plus, Pencil, Trash2, RefreshCw, Info, Loader2 } from 'lucide-react'
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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
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

import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  useSecrets,
  useCreateSecret,
  useUpdateSecret,
  useDeleteSecret,
} from '@/hooks/useSecrets'

interface SecretFormData {
  secretKey: string
  value: string
}

export function Secrets() {
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isUpdateDialogOpen, setIsUpdateDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedSecretName, setSelectedSecretName] = useState<string | undefined>()
  const [formData, setFormData] = useState<SecretFormData>({
    secretKey: '',
    value: '',
  })
  const [updateValue, setUpdateValue] = useState('')


  const { data: secretsData, isFetching, refetch } = useSecrets()

  const createMutation = useCreateSecret()
  const updateMutation = useUpdateSecret()
  const deleteMutation = useDeleteSecret()

  const handleCreate = () => {
    setFormData({ secretKey: '', value: '' })
    setIsCreateDialogOpen(true)
  }

  const handleUpdate = (secretName: string) => {
    setSelectedSecretName(secretName)
    setUpdateValue('')
    setIsUpdateDialogOpen(true)
  }

  const handleDelete = (secretName: string) => {
    setSelectedSecretName(secretName)
    setIsDeleteDialogOpen(true)
  }

  const handleSubmitCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    await createMutation.mutateAsync({
      orgId: 'GLOBAL',
      secretKey: formData.secretKey,
      value: formData.value,
    })
    setIsCreateDialogOpen(false)
    setFormData({ secretKey: '', value: '' })
  }

  const handleSubmitUpdate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedSecretName || !updateValue) return

    await updateMutation.mutateAsync({
      secretName: selectedSecretName,
      data: { value: updateValue },
    })
    setIsUpdateDialogOpen(false)
    setSelectedSecretName(undefined)
    setUpdateValue('')
  }

  const handleConfirmDelete = async () => {
    if (!selectedSecretName) return

    await deleteMutation.mutateAsync(selectedSecretName)
    setIsDeleteDialogOpen(false)
    setSelectedSecretName(undefined)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] space-y-6">
      <div className="flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-extrabold tracking-tight">Secrets Management</h1>
            <p className="mt-2 text-muted-foreground">
              Manage Azure Key Vault secrets for secure configuration storage
            </p>
            <p className="mt-1 text-sm text-muted-foreground">
              These secrets can be referenced in Config entries using type <code className="px-1.5 py-0.5 bg-muted rounded text-xs">secret_ref</code>
            </p>
          </div>
          <Button variant="outline" size="icon" onClick={handleCreate} title="Create Secret">
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Secrets are stored in Azure Key Vault and are not scoped by organization. All secrets are shared across the platform and can be referenced in any organization's configuration.
        </AlertDescription>
      </Alert>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <CardHeader className="flex-shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>All Secrets</CardTitle>
              <CardDescription>
                View and manage secrets stored in Azure Key Vault
              </CardDescription>
            </div>
            <Button variant="outline" size="icon" onClick={() => refetch()} disabled={isFetching}>
              <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden flex flex-col">
          {isFetching ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : secretsData && secretsData.secrets.length > 0 ? (
            <div className="border rounded-lg overflow-hidden flex-1">
              <div className="overflow-auto max-h-full">
                <Table>
                  <TableHeader className="sticky top-0 bg-background z-10">
                    <TableRow>
                      <TableHead>Secret Name</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {secretsData.secrets.map((secretName) => (
                      <TableRow key={secretName} className="hover:bg-muted/50">
                        <TableCell className="font-mono font-medium">{secretName}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleUpdate(secretName)}
                              title="Update secret value"
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(secretName)}
                              title="Delete secret"
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Key className="h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-semibold">No secrets found</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Create your first secret to get started
              </p>
              <Button variant="outline" size="icon" onClick={handleCreate} title="Create Secret" className="mt-4">
                <Plus className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <form onSubmit={handleSubmitCreate}>
            <DialogHeader>
              <DialogTitle>Create Secret</DialogTitle>
              <DialogDescription>
                Add a new secret to Azure Key Vault. The secret will be encrypted and stored securely.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="secretKey">Secret Name *</Label>
                <Input
                  id="secretKey"
                  value={formData.secretKey}
                  onChange={(e) => setFormData({ ...formData, secretKey: e.target.value })}
                  placeholder="AzureOpenAI"
                  pattern="[a-zA-Z0-9_-]+"
                  title="Only alphanumeric characters, hyphens, and underscores allowed"
                  required
                  className="font-mono"
                />
                <p className="text-xs text-muted-foreground">
                  The name of the secret in Azure Key Vault. Use for reference in configs.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="value">Secret Value *</Label>
                <Input
                  id="value"
                  type="password"
                  value={formData.value}
                  onChange={(e) => setFormData({ ...formData, value: e.target.value })}
                  placeholder="Enter secret value"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  This value will be encrypted and stored securely
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending || !formData.secretKey || !formData.value}
              >
                {createMutation.isPending ? 'Creating...' : 'Create Secret'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Update Dialog */}
      <Dialog open={isUpdateDialogOpen} onOpenChange={setIsUpdateDialogOpen}>
        <DialogContent>
          <form onSubmit={handleSubmitUpdate}>
            <DialogHeader>
              <DialogTitle>Update Secret</DialogTitle>
              <DialogDescription>
                Update the value for secret: {selectedSecretName}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="updateValue">New Secret Value *</Label>
                <Input
                  id="updateValue"
                  type="password"
                  value={updateValue}
                  onChange={(e) => setUpdateValue(e.target.value)}
                  placeholder="Enter new secret value"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  This will replace the existing secret value
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsUpdateDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={updateMutation.isPending || !updateValue}
              >
                {updateMutation.isPending ? 'Updating...' : 'Update Secret'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the secret "{selectedSecretName}".
              This action cannot be undone. Any configurations referencing this secret will fail.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete Secret'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
