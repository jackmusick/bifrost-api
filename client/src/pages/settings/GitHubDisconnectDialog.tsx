import type { RefObject } from "react";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

export function GitHubDisconnectDialog({ open, pending, failed, completed, returnFocusRef, onClose, onConfirm }: {
 open: boolean;
 pending: boolean;
 failed: boolean;
 completed: boolean;
 returnFocusRef: RefObject<HTMLElement | null>;
 onClose: () => void;
 onConfirm: () => void;
}) {
 const focus = useDialogReturnFocus(returnFocusRef, completed);
 return <Dialog open={open} onOpenChange={(next) => { if (!next && !pending) onClose(); }}>
  <DialogContent {...focus} onEscapeKeyDown={(e) => { if (pending) e.preventDefault(); }} onPointerDownOutside={(e) => { if (pending) e.preventDefault(); }}>
   <DialogHeader><DialogTitle>Disconnect GitHub Integration</DialogTitle><DialogDescription>This removes the stored GitHub credentials. You will need to configure the integration again to reconnect.</DialogDescription></DialogHeader>
   {failed && <p role="alert" className="text-sm text-destructive">Could not disconnect GitHub. Try again.</p>}
   <DialogFooter>
    <Button variant="outline" className="min-h-11" disabled={pending} onClick={onClose}>Cancel</Button>
    <Button variant="destructive" className="min-h-11" disabled={pending} onClick={onConfirm}>{pending ? "Disconnecting…" : "Disconnect"}</Button>
   </DialogFooter>
  </DialogContent>
 </Dialog>;
}
