import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2 } from 'lucide-react'
import type { Form, FormField, FormSubmission } from '@/types/form'
import { useSubmitForm } from '@/hooks/useForms'
import { useUser } from '@/contexts/UserContext'
import { dataProvidersService, type DataProviderOption } from '@/services/dataProviders'

interface FormRendererProps {
  form: Form
  onSuccess?: (executionResult: any) => void
}

export function FormRenderer({ form, onSuccess }: FormRendererProps) {
  const submitForm = useSubmitForm()
  const { orgId } = useUser()

  // State for data provider options
  const [dataProviderOptions, setDataProviderOptions] = useState<Record<string, DataProviderOption[]>>({})
  const [loadingProviders, setLoadingProviders] = useState<Record<string, boolean>>({})

  // Load data provider options for fields with data providers
  useEffect(() => {
    const loadDataProviders = async () => {
      const selectFields = form.formSchema.fields.filter(
        (field) => field.dataProvider
      )

      for (const field of selectFields) {
        if (!field.dataProvider || typeof field.dataProvider !== 'string') continue

        const providerName = field.dataProvider as string

        // Skip if already loading or loaded
        if (loadingProviders[providerName] || dataProviderOptions[providerName]) {
          continue
        }

        try {
          setLoadingProviders((prev) => ({ ...prev, [providerName]: true }))
          const options = await dataProvidersService.getOptions(providerName)
          setDataProviderOptions((prev) => ({ ...prev, [providerName]: options }))
        } catch (error) {
          console.error(`Failed to load data provider ${providerName}:`, error)
        } finally {
          setLoadingProviders((prev) => ({ ...prev, [providerName]: false }))
        }
      }
    }

    loadDataProviders()
  }, [form.formSchema.fields])

  // Build Zod schema dynamically from form fields
  const buildSchema = () => {
    const schemaFields: Record<string, z.ZodTypeAny> = {}

    form.formSchema.fields.forEach((field) => {
      let fieldSchema: z.ZodTypeAny

      switch (field.type) {
        case 'email':
          fieldSchema = z.string().email('Invalid email address')
          break
        case 'number':
          fieldSchema = z.coerce.number()
          break
        case 'checkbox':
          fieldSchema = z.boolean()
          break
        default:
          fieldSchema = z.string()
      }

      // Apply required validation
      if (field.required) {
        if (field.type === 'checkbox') {
          fieldSchema = z.boolean().refine((val) => val === true, {
            message: 'This field is required',
          })
        } else {
          fieldSchema = fieldSchema.refine((val) => val !== '', {
            message: 'This field is required',
          })
        }
      } else {
        fieldSchema = fieldSchema.optional()
      }

      schemaFields[field.name] = fieldSchema
    })

    return z.object(schemaFields)
  }

  const schema = buildSchema()

  const {
    register,
    handleSubmit,
    formState: { errors },
    setValue,
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: form.formSchema.fields.reduce(
      (acc, field) => {
        acc[field.name] = field.defaultValue || (field.type === 'checkbox' ? false : '')
        return acc
      },
      {} as Record<string, unknown>
    ),
  })

  const onSubmit = async (data: Record<string, unknown>) => {
    const submission = {
      formId: form.id,
      formData: data,
      orgId: form.orgId, // Use the form's orgId to query correct partition
    }

    const result = await submitForm.mutateAsync(submission)
    if (onSuccess) {
      onSuccess(result)
    }
  }

  const renderField = (field: FormField) => {
    const error = errors[field.name]

    // If field has a data provider, render it as a dropdown regardless of type
    if (field.dataProvider) {
      const providerName = typeof field.dataProvider === 'string' ? field.dataProvider : undefined
      const options = providerName ? dataProviderOptions[providerName] : []
      const isLoadingOptions = providerName ? loadingProviders[providerName] : false

      return (
        <div className="space-y-2">
          <Label htmlFor={field.name}>
            {field.label}
            {field.required && <span className="text-destructive ml-1">*</span>}
          </Label>
          <Select
            onValueChange={(value) => setValue(field.name, value)}
            {...(isLoadingOptions !== undefined ? { disabled: isLoadingOptions } : {})}
          >
            <SelectTrigger id={field.name}>
              <SelectValue placeholder={
                isLoadingOptions
                  ? 'Loading options...'
                  : field.placeholder || 'Select an option...'
              } />
            </SelectTrigger>
            <SelectContent>
              {isLoadingOptions ? (
                <div className="flex items-center justify-center p-2 text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Loading...
                </div>
              ) : options && options.length > 0 ? (
                options.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="__no_options__" disabled>
                  No options available
                </SelectItem>
              )}
            </SelectContent>
          </Select>
          {field.helpText && (
            <p className="text-sm text-muted-foreground">{field.helpText}</p>
          )}
          {error && (
            <p className="text-sm text-destructive">{error.message as string}</p>
          )}
        </div>
      )
    }

    switch (field.type) {
      case 'textarea':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Textarea
              id={field.name}
              placeholder={field.placeholder ?? undefined}
              {...register(field.name)}
            />
            {field.helpText && (
              <p className="text-sm text-muted-foreground">{field.helpText}</p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error.message as string}</p>
            )}
          </div>
        )

      case 'checkbox':
        return (
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id={field.name}
                onCheckedChange={(checked) => setValue(field.name, checked)}
              />
              <Label htmlFor={field.name} className="cursor-pointer">
                {field.label}
                {field.required && <span className="text-destructive ml-1">*</span>}
              </Label>
            </div>
            {field.helpText && (
              <p className="text-sm text-muted-foreground">{field.helpText}</p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error.message as string}</p>
            )}
          </div>
        )

      case 'select':
        const providerName = typeof field.dataProvider === 'string' ? field.dataProvider : undefined
        const options = providerName ? dataProviderOptions[providerName] : []
        const isLoadingOptions = providerName ? loadingProviders[providerName] : false

        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Select
              onValueChange={(value) => setValue(field.name, value)}
              {...(isLoadingOptions !== undefined ? { disabled: isLoadingOptions } : {})}
            >
              <SelectTrigger id={field.name}>
                <SelectValue placeholder={
                  isLoadingOptions
                    ? 'Loading options...'
                    : field.placeholder || 'Select an option...'
                } />
              </SelectTrigger>
              <SelectContent>
                {isLoadingOptions ? (
                  <div className="flex items-center justify-center p-2 text-sm text-muted-foreground">
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Loading...
                  </div>
                ) : options && options.length > 0 ? (
                  options.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))
                ) : (
                  <SelectItem value="__no_options__" disabled>
                    No options available
                  </SelectItem>
                )}
              </SelectContent>
            </Select>
            {field.helpText && (
              <p className="text-sm text-muted-foreground">{field.helpText}</p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error.message as string}</p>
            )}
          </div>
        )

      default:
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Input
              id={field.name}
              type={field.type === 'email' ? 'email' : field.type === 'number' ? 'number' : 'text'}
              placeholder={field.placeholder ?? undefined}
              {...register(field.name)}
            />
            {field.helpText && (
              <p className="text-sm text-muted-foreground">{field.helpText}</p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error.message as string}</p>
            )}
          </div>
        )
    }
  }

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-2xl">
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {form.formSchema.fields.map((field, index) => (
              <div key={index}>{renderField(field)}</div>
            ))}
            <div className="pt-4">
              <Button type="submit" disabled={submitForm.isPending}>
                {submitForm.isPending ? 'Submitting...' : 'Submit'}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
