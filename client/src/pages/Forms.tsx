import { useNavigate } from 'react-router-dom'
import { Plus, RefreshCw, FileCode, Pencil, Trash2, PlayCircle, Globe, Building2, Power, PowerOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useForms, useDeleteForm, useUpdateForm } from '@/hooks/useForms'
import { useOrgScope } from '@/contexts/OrgScopeContext'
import { useAuth } from '@/hooks/useAuth'

export function Forms() {
  const navigate = useNavigate()
  const { scope, isGlobalScope } = useOrgScope()
  const { data: forms, isLoading, refetch } = useForms()
  const deleteForm = useDeleteForm()
  const updateForm = useUpdateForm()
  const { isPlatformAdmin } = useAuth()

  // For now, only platform admins can manage forms
  // TODO: Add organization-specific permission check via API
  const canManageForms = isPlatformAdmin

  const handleCreate = () => {
    navigate('/forms/new')
  }

  const handleEdit = (formId: string) => {
    navigate(`/forms/${formId}/edit`)
  }

  const handleDelete = (formId: string, formName: string) => {
    if (confirm(`Are you sure you want to delete form "${formName}"?`)) {
      deleteForm.mutate(formId)
    }
  }

  const handleToggleActive = async (formId: string, currentlyActive: boolean) => {
    await updateForm.mutateAsync({
      formId,
      request: {
        name: null,
        description: null,
        linkedWorkflow: null,
        formSchema: null,
        isActive: !currentlyActive,
        // NEW MVP fields (optional)
        launchWorkflowId: null,
        allowedQueryParams: null,
        defaultLaunchParams: null,
      }
    })
  }

  const handleLaunch = (formId: string) => {
    navigate(`/execute/${formId}`)
  }

  // Filter forms based on scope (only for platform admins)
  const filteredForms = forms?.filter(form => {
    // Regular users: show all forms returned by backend (backend handles authorization)
    if (!isPlatformAdmin) {
      return true
    }

    // Platform admin filtering based on scope switcher:
    // - No org selected (global scope): show all forms
    if (!scope.orgId) {
      return true
    }
    // - Global scope selected: show only global forms
    if (isGlobalScope) {
      return form.isGlobal === true
    }
    // - Org scope selected: show org-specific forms
    return form.orgId === scope.orgId
  }) || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-extrabold tracking-tight">Forms</h1>
            {isPlatformAdmin && (
              <Badge variant={isGlobalScope ? 'default' : 'outline'} className="text-sm">
                {isGlobalScope ? (
                  <>
                    <Globe className="mr-1 h-3 w-3" />
                    Global
                  </>
                ) : (
                  <>
                    <Building2 className="mr-1 h-3 w-3" />
                    {scope.orgName}
                  </>
                )}
              </Badge>
            )}
          </div>
          <p className="mt-2 text-muted-foreground">
            {canManageForms ? 'Launch workflows with guided form interfaces' : 'Launch workflows with guided forms'}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => refetch()} title="Refresh">
            <RefreshCw className="h-4 w-4" />
          </Button>
          {canManageForms && (
            <Button variant="outline" size="icon" onClick={handleCreate} title="Create Form">
              <Plus className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-64 w-full" />
          ))}
        </div>
      ) : filteredForms && filteredForms.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredForms.map((form) => (
            <Card key={form.id} className="hover:border-primary transition-colors flex flex-col">
              <CardHeader>
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg">{form.name}</CardTitle>
                    <CardDescription className="mt-1 min-h-[20px]">
                      {form.description || <span className="italic">No description</span>}
                    </CardDescription>
                  </div>
                  <div className="flex flex-col gap-2 items-end shrink-0">
                    {canManageForms && (
                      <Button
                        variant={form.isActive ? "default" : "outline"}
                        size="sm"
                        onClick={() => handleToggleActive(form.id, form.isActive)}
                        className="h-8 gap-1.5"
                      >
                        {form.isActive ? (
                          <>
                            <Power className="h-3.5 w-3.5" />
                            <span className="text-xs">Enabled</span>
                          </>
                        ) : (
                          <>
                            <PowerOff className="h-3.5 w-3.5" />
                            <span className="text-xs">Disabled</span>
                          </>
                        )}
                      </Button>
                    )}
                    {!form.isActive && !canManageForms && (
                      <Badge variant="secondary">
                        Inactive
                      </Badge>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 flex flex-col">
                <div className="space-y-2 text-sm flex-1">
                  <div>
                    <span className="text-muted-foreground">Workflow:</span>{' '}
                    <span className="font-mono text-xs">{form.linkedWorkflow}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">Fields:</span>{' '}
                    {form.formSchema?.fields?.length || 0} field{form.formSchema?.fields?.length !== 1 ? 's' : ''}
                  </div>
                </div>

                <div className="flex gap-2 mt-4">
                  <Button
                    className="flex-1"
                    onClick={() => handleLaunch(form.id)}
                    disabled={!form.isActive}
                  >
                    <PlayCircle className="mr-2 h-4 w-4" />
                    Launch
                  </Button>
                  {canManageForms && (
                    <>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => handleEdit(form.id)}
                        title="Edit form"
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => handleDelete(form.id, form.name)}
                        title="Delete form"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <FileCode className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">No forms found</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              {canManageForms
                ? 'Get started by creating your first form'
                : 'No forms are currently available'
              }
            </p>
            {canManageForms && (
              <Button variant="outline" size="icon" onClick={handleCreate} className="mt-4" title="Create Form">
                <Plus className="h-4 w-4" />
              </Button>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
