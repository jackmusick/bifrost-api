import { useNavigate } from 'react-router-dom'
import { PlayCircle, FileCode } from 'lucide-react'
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
import { useForms } from '@/hooks/useForms'
import { useUser } from '@/contexts/UserContext'

export function ExecuteForms() {
  const navigate = useNavigate()
  const { isLoading: userLoading } = useUser()
  const { data: forms, isLoading } = useForms()

  // Filter only active forms
  const activeForms = forms?.filter((form) => form.isActive) || []

  const handleExecute = (formId: string) => {
    navigate(`/execute/${formId}`)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight">Execute Forms</h1>
        <p className="mt-2 text-muted-foreground">
          Select a form to execute a workflow with a guided interface
        </p>
      </div>

      {isLoading || userLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-48 w-full" />
          ))}
        </div>
      ) : activeForms.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {activeForms.map((form) => (
            <Card key={form.id} className="hover:border-primary transition-colors">
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  {form.name}
                  {form.isGlobal && (
                    <Badge variant="secondary" className="ml-2">
                      Global
                    </Badge>
                  )}
                </CardTitle>
                {form.description && (
                  <CardDescription>{form.description}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Workflow</p>
                  <p className="font-mono text-sm mt-1">{form.linkedWorkflow}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Fields</p>
                  <p className="text-sm mt-1">
                    {form.formSchema.fields.length} field
                    {form.formSchema.fields.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <Button
                  className="w-full"
                  onClick={() => handleExecute(form.id)}
                >
                  <PlayCircle className="mr-2 h-4 w-4" />
                  Execute Workflow
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <FileCode className="h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-semibold">No active forms available</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Contact your administrator to create and activate forms
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
