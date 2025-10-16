import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, Save, Eye, Settings2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import { useForm as useFormQuery, useCreateForm, useUpdateForm } from '@/hooks/useForms'
import { FormInfoDialog } from '@/components/forms/FormInfoDialog'
import { FieldsPanelDnD } from '@/components/forms/FieldsPanelDnD'
import { FormPreview } from '@/components/forms/FormPreview'
import { useOrgScope } from '@/contexts/OrgScopeContext'
import type { components } from '@/lib/v1'
type FormField = components['schemas']['FormField']
type CreateFormRequest = components['schemas']['CreateFormRequest']
type UpdateFormRequest = components['schemas']['UpdateFormRequest']
import { toast } from 'sonner'

export function FormBuilder() {
  const navigate = useNavigate()
  const { formId } = useParams()
  const isEditing = !!formId
  const { isGlobalScope } = useOrgScope()

  const { data: existingForm } = useFormQuery(formId)
  const createForm = useCreateForm()
  const updateForm = useUpdateForm()

  // Form state
  const [formName, setFormName] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [linkedWorkflow, setLinkedWorkflow] = useState('')
  const [isGlobal, setIsGlobal] = useState(isGlobalScope) // Default based on current scope
  const [fields, setFields] = useState<FormField[]>([])
  const [isInfoDialogOpen, setIsInfoDialogOpen] = useState(false)

  // Load existing form data
  useEffect(() => {
    if (existingForm) {
      setFormName(existingForm.name)
      setFormDescription(existingForm.description || '')
      setLinkedWorkflow(existingForm.linkedWorkflow)
      setIsGlobal(existingForm.isGlobal)
      setFields(existingForm.formSchema.fields)
    }
  }, [existingForm])

  // Update isGlobal when scope changes (only for new forms)
  useEffect(() => {
    if (!isEditing) {
      setIsGlobal(isGlobalScope)
    }
  }, [isGlobalScope, isEditing])

  // Open info dialog automatically for new forms
  useEffect(() => {
    if (!isEditing && !formName) {
      setIsInfoDialogOpen(true)
    }
  }, [isEditing, formName])

  const handleSave = async () => {
    try {
      if (isEditing && formId) {
        const updateRequest: UpdateFormRequest = {
          name: formName,
          description: formDescription || null,
          linkedWorkflow,
          formSchema: { fields },
          isActive: true,
        }
        await updateForm.mutateAsync({ formId, request: updateRequest })
        toast.success('Form updated successfully')
      } else {
        const createRequest: CreateFormRequest = {
          name: formName,
          description: formDescription || null,
          linkedWorkflow,
          formSchema: { fields },
          isGlobal,
          isPublic: false,
        }
        await createForm.mutateAsync(createRequest)
        toast.success('Form created successfully')
      }

      navigate('/forms')
    } catch (error: unknown) {
      console.error('Failed to save form:', error)

      // Extract error message from response
      const errorResponse = error as { response?: { data?: { message?: string; details?: { errors?: { loc: string[], msg: string }[] } } } } & Error
      const errorMessage = errorResponse?.response?.data?.message || errorResponse?.message || 'Failed to save form'
      const errorDetails = errorResponse?.response?.data?.details

      if (errorDetails?.errors) {
        // Show validation errors
        const validationErrors = errorDetails.errors
          .map((err: { loc: string[], msg: string }) => `${err.loc.join('.')}: ${err.msg}`)
          .join('\n')
        toast.error(`Validation Error\n${validationErrors}`)
      } else {
        toast.error(errorMessage)
      }
    }
  }

  const isSaveDisabled = !formName || !linkedWorkflow || fields.length === 0

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate('/forms')}
          >
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-4xl font-extrabold tracking-tight">
                {formName || (isEditing ? 'Edit Form' : 'New Form')}
              </h1>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsInfoDialogOpen(true)}
              >
                <Settings2 className="mr-2 h-4 w-4" />
                {formName ? 'Edit Info' : 'Set Info'}
              </Button>
            </div>
            <div className="mt-2 flex items-center gap-2">
              {linkedWorkflow && (
                <Badge variant="outline" className="font-mono text-xs">
                  {linkedWorkflow}
                </Badge>
              )}
              {isGlobal && (
                <Badge variant="secondary" className="text-xs">
                  Global
                </Badge>
              )}
              {formDescription && (
                <p className="text-sm text-muted-foreground">{formDescription}</p>
              )}
            </div>
          </div>
        </div>
        <Button
          onClick={handleSave}
          disabled={isSaveDisabled || createForm.isPending || updateForm.isPending}
        >
          <Save className="mr-2 h-4 w-4" />
          {createForm.isPending || updateForm.isPending ? 'Saving...' : 'Save Form'}
        </Button>
      </div>

      <Tabs defaultValue="builder" className="w-full">
        <TabsList>
          <TabsTrigger value="builder">Form Builder</TabsTrigger>
          <TabsTrigger value="preview">
            <Eye className="mr-2 h-4 w-4" />
            Preview
          </TabsTrigger>
        </TabsList>

        <TabsContent value="builder" className="mt-6">
          <FieldsPanelDnD fields={fields} setFields={setFields} linkedWorkflow={linkedWorkflow} />
        </TabsContent>

        <TabsContent value="preview" className="mt-6">
          <FormPreview
            formName={formName}
            formDescription={formDescription}
            fields={fields}
          />
        </TabsContent>
      </Tabs>

      <FormInfoDialog
        open={isInfoDialogOpen}
        onClose={() => setIsInfoDialogOpen(false)}
        onSave={(info) => {
          setFormName(info.formName)
          setFormDescription(info.formDescription)
          setLinkedWorkflow(info.linkedWorkflow)
          setIsGlobal(info.isGlobal)
        }}
        initialData={{
          formName,
          formDescription,
          linkedWorkflow,
          isGlobal,
        }}
      />
    </div>
  )
}
