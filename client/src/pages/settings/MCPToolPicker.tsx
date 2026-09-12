import { useId, useState } from "react";
import { X, ChevronsUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem } from "@/components/ui/command";
import type { components } from "@/lib/v1";

export function MCPToolPicker({ title, description, tools, selected, disabled, onToggle, onRemove }: {
 title: string; description: string; tools: components["schemas"]["MCPToolInfo"][]; selected: string[]; disabled: boolean;
 onToggle: (id:string)=>void; onRemove:(id:string)=>void;
}) {
 const [open,setOpen]=useState(false);
 const id=useId();
 return <section aria-labelledby={id} className="min-w-0 space-y-3">
  <h3 id={id} className="text-base font-medium">{title}</h3><p className="text-sm text-muted-foreground">{description}</p>
  {selected.length>0 && <ul className="divide-y rounded-[var(--bf-radius-control)] border px-3">{selected.map(toolId=><li key={toolId} className="flex min-w-0 items-center gap-3 py-2"><span className="min-w-0 flex-1 text-sm [overflow-wrap:anywhere]">{tools.find(tool=>tool.id===toolId)?.name || toolId}</span><Button type="button" variant="ghost" className="size-11 shrink-0" disabled={disabled} aria-label={`Remove ${toolId} from ${title}`} onClick={()=>onRemove(toolId)}><X aria-hidden="true" className="size-4" /></Button></li>)}</ul>}
  <Popover open={open} onOpenChange={setOpen}><PopoverTrigger asChild><Button type="button" variant="outline" role="combobox" aria-label={`Select ${title}`} aria-expanded={open} className="min-h-11 w-full justify-between" disabled={disabled}>Select tools<ChevronsUpDown aria-hidden="true" className="size-4 shrink-0" /></Button></PopoverTrigger>
   <PopoverContent variant="picker" align="start" className="p-0"><Command><CommandInput placeholder="Search tools…" /><CommandList><CommandEmpty>No tools found.</CommandEmpty><CommandGroup>{tools.map(tool=><CommandItem key={tool.id} value={tool.id} keywords={[tool.name,tool.description]} data-checked={selected.includes(tool.id)} disabled={disabled} onSelect={()=>onToggle(tool.id)} className="min-h-11 items-start"><div className="min-w-0 flex-1 space-y-1 [overflow-wrap:anywhere]"><p className="font-mono text-sm">{tool.id}</p><p className="text-sm text-muted-foreground">{tool.description}</p></div></CommandItem>)}</CommandGroup></CommandList></Command></PopoverContent>
  </Popover>
 </section>;
}
