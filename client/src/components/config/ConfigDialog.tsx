import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import * as z from 'zod'
import { Check, ChevronsUpDown } from 'lucide-react'
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
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import { useSetConfig } from '@/hooks/useConfig'
import { useSecrets } from '@/hooks/useSecrets'
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
  orgId?: string | undefined
}

export function ConfigDialog({ config, open, onClose, defaultScope = 'GLOBAL', orgId }: ConfigDialogProps) {
  const setConfig = useSetConfig()
  const isEditing = !!config
  const [comboboxOpen, setComboboxOpen] = useState(false)

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

  // Watch the type field to conditionally render secret selector
  const selectedType = form.watch('type')
  const selectedScope = form.watch('scope')

  // Fetch all secrets for the dropdown
  const { data: secretsData, isLoading: secretsLoading } = useSecrets()

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
                  <FormDescription>
                    {selectedType === 'secret_ref' && 'References a secret stored in Azure Key Vault'}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="value"
              render={({ field }) => (
                <FormItem className="flex flex-col">
                  <FormLabel>Value</FormLabel>
                  {selectedType === 'secret_ref' ? (
                    <>
                      <Popover open={comboboxOpen} onOpenChange={setComboboxOpen}>
                        <FormControl>
                          <PopoverTrigger asChild>
                            <Button
                              variant="outline"
                              role="combobox"
                              aria-expanded={comboboxOpen}
                              className={cn(
                                'w-full justify-between font-mono',
                                !field.value && 'text-muted-foreground'
                              )}
                            >
                              {field.value || 'Select a secret...'}
                              <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                            </Button>
                          </PopoverTrigger>
                        </FormControl>
                        <PopoverContent className="p-0" align="start" style={{ width: 'var(--radix-popover-trigger-width)' }}>
                          <Command>
                            <CommandInput placeholder="Search secrets..." />
                            <CommandList>
                              <CommandEmpty>
                                {secretsLoading ? 'Loading secrets...' : 'No secrets found.'}
                              </CommandEmpty>
                              <CommandGroup>
                                {secretsData?.secrets.map((secretName) => (
                                  <CommandItem
                                    key={secretName}
                                    value={secretName}
                                    onSelect={() => {
                                      form.setValue('value', secretName)
                                      setComboboxOpen(false)
                                    }}
                                    className="font-mono"
                                  >
                                    <Check
                                      className={cn(
                                        'mr-2 h-4 w-4',
                                        field.value === secretName ? 'opacity-100' : 'opacity-0'
                                      )}
                                    />
                                    {secretName}
                                  </CommandItem>
                                ))}
                              </CommandGroup>
                            </CommandList>
                          </Command>
                        </PopoverContent>
                      </Popover>
                      <FormDescription>
                        Select a secret name from Azure Key Vault. Scope is determined by this config entry.
                      </FormDescription>
                    </>
                  ) : (
                    <>
                      <FormControl>
                        <Textarea
                          placeholder="Configuration value"
                          className="font-mono"
                          {...field}
                        />
                      </FormControl>
                      <FormDescription>Enter the configuration value</FormDescription>
                    </>
                  )}
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
              <Button
                type="submit"
                disabled={setConfig.isPending || !form.formState.isValid}
              >
                {setConfig.isPending ? 'Saving...' : isEditing ? 'Update' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
