import { useState, useEffect, useMemo, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Card,
  CardContent,
} from '@/components/ui/card'
import { JsxTemplateRenderer } from '@/components/ui/jsx-template-renderer'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { Combobox } from '@/components/ui/combobox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Skeleton } from '@/components/ui/skeleton'
import { Loader2, Upload } from 'lucide-react'
import DOMPurify from 'dompurify'
import ReactMarkdown from 'react-markdown'
import type { components } from '@/lib/v1'

type Form = components['schemas']['Form']
type FormField = components['schemas']['FormField']
import { useSubmitForm } from '@/hooks/useForms'

import { dataProvidersService, type DataProviderOption } from '@/services/dataProviders'
import { FormContextProvider, useFormContext } from '@/contexts/FormContext'
import { useLaunchWorkflow } from '@/hooks/useLaunchWorkflow'

interface FormRendererProps {
  form: Form
}

/**
 * Inner component that uses FormContext
 * Separated to allow FormContextProvider to wrap it
 */
function FormRendererInner({ form }: FormRendererProps) {
  const navigate = useNavigate()
  const submitForm = useSubmitForm()
  const { context, isFieldVisible, setFieldValue, isLoadingLaunchWorkflow } = useFormContext()

  // Execute launch workflow if configured
  useLaunchWorkflow({ form })

  // State for data provider options
  const [dataProviderOptions, setDataProviderOptions] = useState<Record<string, DataProviderOption[]>>({})
  const [loadingProviders, setLoadingProviders] = useState<Record<string, boolean>>({})

  // Load data provider options for fields with data providers
  useEffect(() => {
    const loadDataProviders = async () => {
      const selectFields = form.formSchema?.fields?.filter(
        (field) => field.dataProvider
      ) || []

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
  }, [form.formSchema?.fields, dataProviderOptions, loadingProviders])

  // Build Zod schema dynamically from form fields
  const buildSchema = () => {
    const schemaFields: Record<string, z.ZodTypeAny> = {}

    form.formSchema?.fields?.forEach((field) => {
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
    watch,
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: form.formSchema?.fields?.reduce(
      (acc, field) => {
        acc[field.name] = field.defaultValue || (field.type === 'checkbox' ? false : '')
        return acc
      },
      {} as Record<string, unknown>
    ) || {},
  })

  // Watch all field values and sync to FormContext for visibility evaluation
  // Use ref to track previous values to avoid infinite loops
  const formValues = watch()
  const prevValuesRef = useRef<Record<string, unknown>>({})

  useEffect(() => {
    // Only update fields that have actually changed
    Object.entries(formValues).forEach(([fieldName, value]) => {
      if (prevValuesRef.current[fieldName] !== value) {
        prevValuesRef.current[fieldName] = value
        setFieldValue(fieldName, value)
      }
    })
  }, [formValues, setFieldValue])

  const onSubmit = async (data: Record<string, unknown>) => {
    const submission = {
      formId: form.id,
      formData: data,
      orgId: form.orgId, // Use the form's orgId to query correct partition
    }

    const result = await submitForm.mutateAsync(submission)
    navigate(`/history/${result.executionId}`)
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
          <Combobox
            id={field.name}
            options={options && options.length > 0 ? options : []}
            value={formValues[field.name] as string}
            onValueChange={(value) => setValue(field.name, value)}
            placeholder={field.placeholder || 'Select an option...'}
            emptyText="No options available"
            isLoading={!!isLoadingOptions}
            disabled={!!isLoadingOptions}
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

      case 'select': {
        const providerName = typeof field.dataProvider === 'string' ? field.dataProvider : undefined
        const staticOptions = (field.options || []) as Array<{ label: string; value: string }>
        const dynamicOptions = providerName ? dataProviderOptions[providerName] : []
        const options = providerName ? dynamicOptions : staticOptions
        const isLoadingOptions = providerName ? loadingProviders[providerName] : false

        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Combobox
              id={field.name}
              options={options && options.length > 0 ? options : []}
              value={formValues[field.name] as string}
              onValueChange={(value) => setValue(field.name, value)}
              placeholder={field.placeholder || 'Select an option...'}
              emptyText="No options available"
              isLoading={!!isLoadingOptions}
              disabled={!!isLoadingOptions}
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

      case 'radio': {
        const radioOptions = (field.options || []) as Array<{ label: string; value: string }>
        const defaultVal = field.defaultValue as string | null | undefined
        return (
          <div className="space-y-2">
            <Label>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <RadioGroup
              onValueChange={(value: string) => setValue(field.name, value)}
              {...(defaultVal ? { defaultValue: defaultVal } : {})}
            >
              {radioOptions.map((option) => (
                <div key={option['value']} className="flex items-center space-x-2">
                  <RadioGroupItem value={option['value']} id={`${field.name}-${option['value']}`} />
                  <Label htmlFor={`${field.name}-${option['value']}`} className="cursor-pointer font-normal">
                    {option['label']}
                  </Label>
                </div>
              ))}
            </RadioGroup>
            {field.helpText && (
              <p className="text-sm text-muted-foreground">{field.helpText}</p>
            )}
            {error && (
              <p className="text-sm text-destructive">{error.message as string}</p>
            )}
          </div>
        )
      }

      case 'datetime':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <Input
              id={field.name}
              type="datetime-local"
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

      case 'markdown':
        return (
          <div className="space-y-2">
            <div className="prose prose-sm max-w-none dark:prose-invert">
              {field.content ? (
                <ReactMarkdown
                  components={{
                    // Ensure headings render properly
                    h1: ({...props}) => <h1 className="text-2xl font-bold mt-4 mb-2" {...props} />,
                    h2: ({...props}) => <h2 className="text-xl font-bold mt-3 mb-2" {...props} />,
                    h3: ({...props}) => <h3 className="text-lg font-bold mt-2 mb-1" {...props} />,
                    h4: ({...props}) => <h4 className="text-base font-bold mt-2 mb-1" {...props} />,
                    h5: ({...props}) => <h5 className="text-sm font-bold mt-1 mb-1" {...props} />,
                    h6: ({...props}) => <h6 className="text-xs font-bold mt-1 mb-1" {...props} />,
                  }}
                >
                  {field.content}
                </ReactMarkdown>
              ) : (
                <span className="text-muted-foreground italic">No content provided</span>
              )}
            </div>
            {field.helpText && (
              <p className="text-sm text-muted-foreground">{field.helpText}</p>
            )}
          </div>
        )

      case 'html': {
        // Support both JSX templates and static HTML
        // HTML fields are display-only components and should not show labels
        const content = field.content || '<p className="text-muted-foreground italic">No content provided</p>'

        // Check if content looks like JSX (contains React-style attributes or JSX expressions)
        const isJsxTemplate = content.includes('className=') || content.includes('{context.')

        if (isJsxTemplate) {
          // Render as JSX template with full context access
          return (
            <div className="space-y-2">
              <JsxTemplateRenderer template={content} context={context} />
              {field.helpText && (
                <p className="text-sm text-muted-foreground">{field.helpText}</p>
              )}
            </div>
          )
        } else {
          // Fallback to sanitized HTML for backwards compatibility
          const sanitizedHtml = DOMPurify.sanitize(content)
          return (
            <div className="space-y-2">
              <div
                className="border rounded-md p-4 bg-muted/30"
                dangerouslySetInnerHTML={{ __html: sanitizedHtml }}
              />
              {field.helpText && (
                <p className="text-sm text-muted-foreground">{field.helpText}</p>
              )}
            </div>
          )
        }
      }

      case 'file':
        return (
          <div className="space-y-2">
            <Label htmlFor={field.name}>
              {field.label}
              {field.required && <span className="text-destructive ml-1">*</span>}
            </Label>
            <div className="border-2 border-dashed rounded-lg p-6 hover:border-primary/50 transition-colors">
              <div className="flex flex-col items-center gap-2">
                <Upload className="h-8 w-8 text-muted-foreground" />
                <div className="text-center">
                  <Label htmlFor={field.name} className="cursor-pointer text-sm font-medium text-primary hover:underline">
                    Choose file{field.multiple ? 's' : ''}
                  </Label>
                  <Input
                    id={field.name}
                    type="file"
                    className="hidden"
                    {...register(field.name)}
                    accept={field.allowedTypes?.join(',') ?? undefined}
                    multiple={field.multiple ?? undefined}
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {field.allowedTypes && field.allowedTypes.length > 0
                      ? `Allowed: ${field.allowedTypes.join(', ')}`
                      : 'All file types allowed'}
                    {field.maxSizeMB && ` • Max ${field.maxSizeMB}MB`}
                  </p>
                </div>
              </div>
            </div>
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

  // Filter fields by visibility
  // Context changes trigger re-evaluation through isFieldVisible
  const visibleFields = useMemo(() => {
    return form.formSchema?.fields?.filter(isFieldVisible) || []
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [form.formSchema?.fields, context])

  // Show loading state while launch workflow executes or data providers load
  const isAnyDataProviderLoading = Object.values(loadingProviders).some(loading => loading)
  const showLoadingState = isLoadingLaunchWorkflow || isAnyDataProviderLoading

  if (showLoadingState) {
    return (
      <div className="flex justify-center">
        <Card className="w-full max-w-2xl">
          <CardContent className="pt-6">
            <div className="space-y-6">
              {/* Loading indicator */}
              <div className="flex items-center gap-3 p-4 bg-muted/50 rounded-lg">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    {isLoadingLaunchWorkflow ? 'Loading form data...' : 'Loading form options...'}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {isLoadingLaunchWorkflow
                      ? 'Executing launch workflow to populate form context'
                      : 'Fetching dynamic options from data providers'
                    }
                  </p>
                </div>
              </div>

              {/* Skeleton loader for form fields */}
              <div className="space-y-4">
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-12 w-full" />
                <Skeleton className="h-10 w-32" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-2xl">
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <AnimatePresence mode="popLayout">
              {visibleFields.map((field) => (
                <motion.div
                  key={field.name}
                  initial={{ opacity: 0, height: 0, marginBottom: 0 }}
                  animate={{ opacity: 1, height: 'auto', marginBottom: 16 }}
                  exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                  transition={{
                    opacity: { duration: 0.2 },
                    height: { duration: 0.3, ease: 'easeInOut' },
                    marginBottom: { duration: 0.3, ease: 'easeInOut' }
                  }}
                  style={{ overflow: 'hidden' }}
                >
                  {renderField(field)}
                </motion.div>
              ))}
            </AnimatePresence>
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

/**
 * FormRenderer with FormContext wrapper
 * Extracts query parameters from URL and provides them to context
 */
export function FormRenderer({ form }: FormRendererProps) {
  const [searchParams] = useSearchParams()

  // Convert URLSearchParams to plain object
  const queryParams = useMemo(() => {
    const params: Record<string, string> = {}
    searchParams.forEach((value, key) => {
      params[key] = value
    })
    return params
  }, [searchParams])

  return (
    <FormContextProvider form={form} queryParams={queryParams}>
      <FormRendererInner form={form} />
    </FormContextProvider>
  )
}
