import { CheckCircle2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { GitHubConfigResponse } from "@/hooks/useGitHub";

export function GitHubConnectionSummary({ config, pending, onDisconnect }: {
 config: GitHubConfigResponse;
 pending: boolean;
 onDisconnect: () => void;
}) {
 return <section aria-label="Connected GitHub repository" className="min-w-0 space-y-4">
  <div className="flex flex-wrap items-center justify-between gap-3">
   <p className="flex items-center gap-2 text-sm font-medium"><CheckCircle2 aria-hidden="true" className="size-4 shrink-0 text-[var(--bf-success)]" />Connected</p>
   <Button variant="outline" className="min-h-11" disabled={pending} onClick={onDisconnect}>{pending ? <><Loader2 aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" />Disconnecting…</> : "Disconnect"}</Button>
  </div>
  <dl className="grid min-w-0 gap-4 border-y py-4 text-sm">
   <div className="grid min-w-0 gap-1 sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-4"><dt className="text-muted-foreground">Repository</dt><dd className="min-w-0 font-mono [overflow-wrap:anywhere]">{config.repo_url}</dd></div>
   <div className="grid min-w-0 gap-1 sm:grid-cols-[7rem_minmax(0,1fr)] sm:gap-4"><dt className="text-muted-foreground">Branch</dt><dd className="min-w-0 font-mono [overflow-wrap:anywhere]">{config.branch}</dd></div>
  </dl>
  <p className="text-sm text-muted-foreground">Use the <strong>Source Control</strong> panel in the Code Editor to commit, push, and pull changes.</p>
 </section>;
}
