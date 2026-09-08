import { CheckCircle2, Copy, Settings2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { toast } from "sonner";

export function MCPConnectionDetails({ configured, updatedAt, updatedBy, url }: {
 configured: boolean; updatedAt?: string | null; updatedBy?: string | null; url: string;
}) {
 const copy = async () => {
  try { await navigator.clipboard.writeText(url); toast.success("MCP URL copied to clipboard"); }
  catch { toast.error("Could not copy MCP URL", { description: "Select and copy the URL shown here." }); }
 };
 return <section aria-label="MCP connection details" className="min-w-0 space-y-4">
  <div className="flex items-start gap-3 text-sm">
   {configured ? <CheckCircle2 aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-[var(--bf-success)]" /> : <Settings2 aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />}
   <div className="min-w-0"><p className="font-medium">{configured ? "MCP Configured" : "Using Default Configuration"}</p>{configured && updatedAt && <p className="mt-1 text-muted-foreground [overflow-wrap:anywhere]">Last updated {new Date(updatedAt).toLocaleDateString()}{updatedBy ? ` by ${updatedBy}` : ""}</p>}</div>
  </div>
  <div className="flex min-w-0 items-start gap-3 rounded-[var(--bf-radius-surface)] border p-4">
   <div className="min-w-0 flex-1"><p className="text-sm font-medium">MCP Server URL</p><p className="mt-2 select-text font-mono text-sm text-muted-foreground [overflow-wrap:anywhere]">{url}</p></div>
   <Button type="button" variant="ghost" className="size-11 shrink-0" aria-label="Copy MCP server URL" onClick={() => { void copy(); }}><Copy aria-hidden="true" className="size-4" /></Button>
  </div>
 </section>;
}
