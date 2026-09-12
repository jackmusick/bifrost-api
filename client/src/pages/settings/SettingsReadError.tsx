import { Button } from "@/components/ui/button";

export function SettingsReadError({ resource, cached, pending, onRetry }: {
 resource: string;
 cached: boolean;
 pending: boolean;
 onRetry: () => void;
}) {
 return <div role="alert" className="min-w-0 space-y-3 rounded-[var(--bf-radius-surface)] border bg-[var(--bf-warning-soft)] p-4 text-sm">
  <p>Could not {cached ? "refresh" : "load"} {resource}. {cached ? "Previously loaded details are still shown." : "Retry to load the current configuration."}</p>
  <Button type="button" variant="outline" className="min-h-11" disabled={pending} onClick={onRetry}>Retry {resource}</Button>
 </div>;
}
