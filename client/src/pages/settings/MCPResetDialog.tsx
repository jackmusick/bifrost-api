import type { RefObject } from "react";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

export function MCPResetDialog({ open,pending,failed,completed,returnFocusRef,onClose,onConfirm }: {
 open:boolean; pending:boolean; failed:boolean; completed:boolean; returnFocusRef:RefObject<HTMLElement|null>; onClose:()=>void; onConfirm:()=>void;
}) {
 const focus=useDialogReturnFocus(returnFocusRef,completed);
 return <Dialog open={open} onOpenChange={next=>{if(!next&&!pending)onClose();}}><DialogContent {...focus} onEscapeKeyDown={e=>{if(pending)e.preventDefault();}} onPointerDownOutside={e=>{if(pending)e.preventDefault();}}>
  <DialogHeader><DialogTitle>Reset MCP configuration?</DialogTitle><DialogDescription>This enables external MCP access and clears the allowed and blocked tool lists. Users still see only the agents and tools they have permission to access. Unsaved changes will be discarded.</DialogDescription></DialogHeader>
  {failed&&<p role="alert" className="text-sm text-destructive">Could not reset MCP configuration. Try again.</p>}
  <DialogFooter><Button variant="outline" className="min-h-11" disabled={pending} onClick={onClose}>Cancel</Button><Button className="min-h-11" disabled={pending} onClick={onConfirm}>{pending?"Resetting…":"Reset configuration"}</Button></DialogFooter>
 </DialogContent></Dialog>;
}
