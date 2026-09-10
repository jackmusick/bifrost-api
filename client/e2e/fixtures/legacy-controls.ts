/** Frozen V1 consumer: imports and controlled props remain intentionally ordinary. */
export const LEGACY_CONTROLS_TSX = `import { useState } from "react";
import { Button, Label, Checkbox, Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
 Dialog, DialogTrigger, DialogContent, DialogTitle, DialogDescription, DialogClose,
 Tabs, TabsList, TabsTrigger, TabsContent, Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
 CommandDialog, CommandInput, CommandList, CommandItem } from "bifrost";
export default function LegacyControls() {
 const [checked, setChecked] = useState(false);
 const [region, setRegion] = useState("east");
 const [commandOpen, setCommandOpen] = useState(false);
 const [command, setCommand] = useState("None");
 return <section aria-label="Legacy included controls" style={{padding:16, display:"grid", gap:16, minWidth:0}}>
  <div><Checkbox id="legacy-notify" checked={checked} onCheckedChange={setChecked} /><Label htmlFor="legacy-notify">Notify owner</Label></div>
  <output aria-label="Notification state">{checked ? "Enabled" : "Disabled"}</output>
  <Select value={region} onValueChange={setRegion}><SelectTrigger aria-label="Region"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="east">East</SelectItem><SelectItem value="west">West</SelectItem></SelectContent></Select>
  <output aria-label="Selected region">{region}</output>
  <Dialog><DialogTrigger asChild><Button>Open legacy dialog</Button></DialogTrigger><DialogContent><DialogTitle>Legacy confirmation</DialogTitle><DialogDescription>Included dialog content remains interactive.</DialogDescription><DialogClose asChild><Button>Done</Button></DialogClose></DialogContent></Dialog>
  <Button onClick={()=>setCommandOpen(true)}>Open legacy commands</Button>
  <CommandDialog open={commandOpen} onOpenChange={setCommandOpen} title="Legacy commands" description="Choose a command"><CommandInput placeholder="Find legacy command" /><CommandList><CommandItem value="archive" onSelect={()=>{setCommand("Archive");setCommandOpen(false);}}>Archive</CommandItem></CommandList></CommandDialog>
  <output aria-label="Chosen command">{command}</output>
  <Tabs defaultValue="summary"><TabsList><TabsTrigger value="summary">Summary</TabsTrigger><TabsTrigger value="records">Records</TabsTrigger></TabsList><TabsContent value="summary">Legacy summary</TabsContent><TabsContent value="records"><Table><TableHeader><TableRow><TableHead>Name</TableHead><TableHead>Status</TableHead></TableRow></TableHeader><TableBody><TableRow><TableCell>Sample record</TableCell><TableCell>Ready</TableCell></TableRow></TableBody></Table></TabsContent></Tabs>
 </section>;
}`;
