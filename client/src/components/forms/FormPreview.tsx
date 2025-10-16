import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import type { components } from '@/lib/v1'
type FormField = components['schemas']['FormField']

interface FormPreviewProps {
  formName: string
  formDescription: string
  fields: FormField[]
}

export function FormPreview({ formName, formDescription, fields }: FormPreviewProps) {
  const renderField = (field: FormField) => {
    switch (field.type) {
      case 'textarea':
        return (
          <Textarea
            placeholder={field.placeholder ?? undefined}
            defaultValue={field.defaultValue as string}
            disabled
          />
        )
      case 'checkbox':
        return (
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id={field.name}
              defaultChecked={field.defaultValue as boolean}
              disabled
              className="h-4 w-4"
            />
            <Label htmlFor={field.name}>{field.label}</Label>
          </div>
        )
      case 'select':
        return (
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background disabled:cursor-not-allowed disabled:opacity-50"
            disabled
          >
            <option>{field.placeholder || 'Select an option...'}</option>
          </select>
        )
      default:
        return (
          <Input
            type={field.type === 'email' ? 'email' : field.type === 'number' ? 'number' : 'text'}
            placeholder={field.placeholder ?? undefined}
            defaultValue={field.defaultValue as string}
            disabled
          />
        )
    }
  }

  return (
    <div className="flex justify-center">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>{formName || 'Form Preview'}</CardTitle>
          {formDescription && <CardDescription>{formDescription}</CardDescription>}
        </CardHeader>
        <CardContent>
          {fields.length > 0 ? (
            <div className="space-y-4">
              {fields.map((field, index) => (
                <div key={index} className="space-y-2">
                  {field.type !== 'checkbox' && (
                    <Label>
                      {field.label}
                      {field.required && <span className="text-destructive ml-1">*</span>}
                    </Label>
                  )}
                  {renderField(field)}
                  {field.helpText && (
                    <p className="text-sm text-muted-foreground">{field.helpText}</p>
                  )}
                </div>
              ))}
              <div className="pt-4">
                <Button disabled>Submit</Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <p className="text-sm text-muted-foreground">
                Add fields to see the form preview
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
