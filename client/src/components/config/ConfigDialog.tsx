import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useSetConfig } from '@/hooks/useConfig'
import type { Config, ConfigScope } from '@/types/config'

const formSchema = z.object({
  key: z.string().min(1, 'Key is required').regex(/^[a-zA-Z0-9_]+$/, 'Key must be alphanumeric with underscores'),
  value: z.string().min(1, 'Value is required'),
  type: z.enum(['string', 'int', 'bool', 'json', 'secret_ref']),
  scope: z.enum(['GLOBAL', 'org']),
  description: z.string().optional(),
})

type FormValues = z.infer<typeof formSchema>

interface ConfigDialogProps {
  config?: Config | undefined
  open: boolean
  onClose: () => void
  defaultScope?: ConfigScope | undefined
}

export function ConfigDialog({ config, open, onClose, defaultScope = 'GLOBAL' }: ConfigDialogProps) {
  const setConfig = useSetConfig()
  const isEditing = !!config

  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      key: '',
      value: '',
      type: 'string',
      scope: defaultScope,
      description: '',
    },
  })

  useEffect(() => {
    if (config) {
      form.reset({
        key: config.key,
        value: config.value,
        type: config.type,
        scope: config.scope,
        description: config.description || '',
      })
    } else {
      form.reset({
        key: '',
        value: '',
        type: 'string',
        scope: defaultScope,
        description: '',
      })
    }
  }, [config, defaultScope, form])

  const onSubmit = async (values: FormValues) => {
    await setConfig.mutateAsync({
      key: values.key,
      value: values.value,
      type: values.type,
      scope: values.scope,
      description: values.description ?? null,
    })
    onClose()
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{isEditing ? 'Edit Configuration' : 'Add Configuration'}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? 'Update the configuration value'
              : 'Create a new configuration entry'}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="key"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Key</FormLabel>
                  <FormControl>
                    <Input
                      placeholder="CONFIG_KEY_NAME"
                      {...field}
                      disabled={isEditing}
                      className="font-mono"
                    />
                  </FormControl>
                  <FormDescription>
                    Alphanumeric characters and underscores only
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Type</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="string">String</SelectItem>
                        <SelectItem value="int">Integer</SelectItem>
                        <SelectItem value="bool">Boolean</SelectItem>
                        <SelectItem value="json">JSON</SelectItem>
                        <SelectItem value="secret_ref">Secret Reference</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="scope"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Scope</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select scope" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="GLOBAL">Global</SelectItem>
                        <SelectItem value="org">Organization</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="value"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Value</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="Configuration value"
                      className="font-mono"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description (Optional)</FormLabel>
                  <FormControl>
                    <Input placeholder="What is this config for?" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" disabled={setConfig.isPending}>
                {setConfig.isPending ? 'Saving...' : isEditing ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
