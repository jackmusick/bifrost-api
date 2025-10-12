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
import { Badge } from '@/components/ui/badge'

interface FormInfoPanelProps {
  formName: string
  setFormName: (name: string) => void
  formDescription: string
  setFormDescription: (description: string) => void
  linkedWorkflow: string
  setLinkedWorkflow: (workflow: string) => void
  isGlobal: boolean
  setIsGlobal: (isGlobal: boolean) => void
}

export function FormInfoPanel({
  formName,
  setFormName,
  formDescription,
  setFormDescription,
  linkedWorkflow,
  setLinkedWorkflow,
  isGlobal,
  setIsGlobal,
}: FormInfoPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Form Information</CardTitle>
        <CardDescription>
          Basic details about the form and linked workflow
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="formName">Form Name *</Label>
            <Input
              id="formName"
              placeholder="User Onboarding Form"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="linkedWorkflow">Linked Workflow *</Label>
            <Input
              id="linkedWorkflow"
              placeholder="user_onboarding"
              value={linkedWorkflow}
              onChange={(e) => setLinkedWorkflow(e.target.value)}
              className="font-mono"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="formDescription">Description</Label>
          <Textarea
            id="formDescription"
            placeholder="Describe what this form does..."
            value={formDescription}
            onChange={(e) => setFormDescription(e.target.value)}
          />
        </div>

        <div className="space-y-2">
          <Label>Scope</Label>
          <div className="flex gap-2">
            <button
              onClick={() => setIsGlobal(true)}
              className={`rounded-lg border px-4 py-2 text-sm transition-colors ${
                isGlobal
                  ? 'border-primary bg-primary/5 text-primary'
                  : 'border-border hover:bg-accent'
              }`}
            >
              <Badge variant={isGlobal ? 'default' : 'outline'}>Global</Badge>
              <p className="mt-1 text-xs text-muted-foreground">
                Available to all organizations
              </p>
            </button>
            <button
              onClick={() => setIsGlobal(false)}
              className={`rounded-lg border px-4 py-2 text-sm transition-colors ${
                !isGlobal
                  ? 'border-primary bg-primary/5 text-primary'
                  : 'border-border hover:bg-accent'
              }`}
            >
              <Badge variant={!isGlobal ? 'default' : 'outline'}>Organization-Specific</Badge>
              <p className="mt-1 text-xs text-muted-foreground">
                Specific to one organization
              </p>
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
