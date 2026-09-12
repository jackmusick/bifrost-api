import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function GitHubResourceSelect({ id, value, placeholder, options, disabled, loading, onChange }: {
 id: string;
 value: string;
 placeholder: string;
 options: { value: string; detail?: string }[];
 disabled?: boolean;
 loading?: boolean;
 onChange: (value: string) => void;
}) {
 return <Select value={value} onValueChange={onChange} disabled={disabled || loading}>
  <SelectTrigger id={id} className="data-[size=default]:h-auto min-h-11 w-full [&_[data-slot=select-value]]:min-w-0 [&_[data-slot=select-value]]:whitespace-normal [&_[data-slot=select-value]]:text-left">
   {loading ? <span role="status">Loading branches…</span> : <SelectValue placeholder={placeholder} />}
  </SelectTrigger>
  <SelectContent className="max-w-[calc(100vw-2rem)]">
   {options.map(option => <SelectItem key={option.value} value={option.value} className="min-h-11 whitespace-normal [&>span:last-child]:min-w-0">
    <span className="min-w-0 !block text-left [overflow-wrap:anywhere]"><span className="block">{option.value}</span>{option.detail && <span className="block text-xs text-muted-foreground">{option.detail}</span>}</span>
   </SelectItem>)}
  </SelectContent>
 </Select>;
}
