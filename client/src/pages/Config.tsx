import { useState } from 'react'
import { Pencil, Plus, Trash2, Key, RefreshCw, Globe, Building2 } from 'lucide-react'
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
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useConfigs, useDeleteConfig } from '@/hooks/useConfig'
import { ConfigDialog } from '@/components/config/ConfigDialog'
import { useOrgScope } from '@/contexts/OrgScopeContext'
import type { Config as ConfigType } from '@/types/config'

export function Config() {
  const [selectedConfig, setSelectedConfig] = useState<ConfigType | undefined>()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const { scope, isGlobalScope } = useOrgScope()

  // Fetch configs based on current scope
  const scopeParam = isGlobalScope ? 'GLOBAL' : 'org'
  const { data: configs, isLoading, refetch } = useConfigs(scopeParam, scope.orgId ?? undefined)
  const deleteConfig = useDeleteConfig()

  const handleEdit = (config: ConfigType) => {
    setSelectedConfig(config)
    setIsDialogOpen(true)
  }

  const handleAdd = () => {
    setSelectedConfig(undefined)
    setIsDialogOpen(true)
  }

  const handleDelete = (config: ConfigType) => {
    if (confirm(`Are you sure you want to delete config "${config.key}"?`)) {
      deleteConfig.mutate({ key: config.key, scope: config.scope, orgId: config.orgId ?? null })
    }
  }

  const handleDialogClose = () => {
    setIsDialogOpen(false)
    setSelectedConfig(undefined)
  }

  const getTypeBadge = (type: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
      string: 'default',
      int: 'secondary',
      bool: 'outline',
      json: 'secondary',
      secret_ref: 'destructive',
    }
    return <Badge variant={variants[type] || 'default'}>{type}</Badge>
  }

  const maskValue = (value: string, type: string) => {
    if (type === 'secret_ref') {
      return '••••••••'
    }
    if (value.length > 50) {
      return value.substring(0, 50) + '...'
    }
    return value
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-4xl font-extrabold tracking-tight">Configuration</h1>
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
          </div>
          <p className="mt-2 text-muted-foreground">
            {isGlobalScope
              ? 'Platform-wide configuration values'
              : `Configuration for ${scope.orgName}`}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="icon" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          <Button onClick={handleAdd}>
            <Plus className="mr-2 h-4 w-4" />
            Add Config
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <div>
            <CardTitle>
              {isGlobalScope ? 'Global' : 'Organization'} Configuration
            </CardTitle>
            <CardDescription>
              {isGlobalScope
                ? 'Platform-wide configuration values'
                : 'Organization-specific configuration overrides'}
            </CardDescription>
          </div>
        </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="space-y-2">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-12 w-full" />
                  ))}
                </div>
              ) : configs && configs.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Key</TableHead>
                      <TableHead>Value</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {configs.map((config) => (
                      <TableRow key={`${config.scope}-${config.key}`}>
                        <TableCell className="font-mono">{config.key}</TableCell>
                        <TableCell className="max-w-xs truncate">
                          {maskValue(config.value, config.type)}
                        </TableCell>
                        <TableCell>{getTypeBadge(config.type)}</TableCell>
                        <TableCell className="max-w-xs truncate text-muted-foreground">
                          {config.description || '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleEdit(config)}
                            >
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleDelete(config)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <Key className="h-12 w-12 text-muted-foreground" />
                  <h3 className="mt-4 text-lg font-semibold">No configuration found</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Get started by creating your first config entry
                  </p>
                  <Button onClick={handleAdd} className="mt-4">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Config
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

      <ConfigDialog
        config={selectedConfig}
        open={isDialogOpen}
        onClose={handleDialogClose}
        defaultScope={scopeParam}
        orgId={scope.orgId ?? undefined}
      />
    </div>
  )
}
