import { Button } from "@/components/ui/button";

export function FleetReadError({ resource, cached, pending, onRetry }: { resource:string; cached:boolean; pending:boolean; onRetry:()=>void }) {
 return <div role="alert" className="min-w-0 space-y-3 rounded-[var(--bf-radius-surface)] border bg-[var(--bf-warning-soft)] p-4 text-sm">
  <p>Could not {cached?"refresh":"load"} {resource}.{cached?" Previously loaded data is still shown.":" Try again to load this information."}</p>
  <Button type="button" variant="outline" className="min-h-11" disabled={pending} onClick={onRetry}>Retry {resource}</Button>
 </div>;
}
