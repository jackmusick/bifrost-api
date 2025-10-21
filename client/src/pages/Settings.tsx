import { useState } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { WorkflowKeys } from '@/pages/WorkflowKeys';
import { Branding } from '@/pages/settings/Branding';

export function Settings() {
  const [activeTab, setActiveTab] = useState('workflow-keys');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-extrabold tracking-tight">Settings</h1>
        <p className="mt-2 text-muted-foreground">
          Manage platform settings and configuration
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="workflow-keys">Workflow Keys</TabsTrigger>
          <TabsTrigger value="branding">Branding</TabsTrigger>
        </TabsList>

        <TabsContent value="workflow-keys" className="mt-6">
          <WorkflowKeys />
        </TabsContent>

        <TabsContent value="branding" className="mt-6">
          <Branding />
        </TabsContent>
      </Tabs>
    </div>
  );
}
