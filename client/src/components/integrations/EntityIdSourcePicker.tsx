import { useId, useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { components } from "@/lib/v1";

export type Candidate = components["schemas"]["EntityIdPickerCandidate"];

interface EntityIdSourcePickerProps {
	candidates: Candidate[];
	onSelect: (candidate: Candidate) => void;
	onSkip: () => void;
	isPending: boolean;
	error?: string | null;
}

export function EntityIdSourcePicker({
	candidates,
	onSelect,
	onSkip,
	isPending,
	error,
}: EntityIdSourcePickerProps) {
	const groupName = useId();
	const [selectedKey, setSelectedKey] = useState<string | null>(null);

	const keyId = (c: Candidate) => `${c.type}:${c.key}`;
	const selected = candidates.find((c) => keyId(c) === selectedKey) ?? null;

	return (
		<div className="space-y-4">
			<div>
				<h3 className="text-lg font-semibold">
					Set up entity ID auto-capture
				</h3>
				<p className="text-sm text-muted-foreground mt-1">
					Pick the field that uniquely identifies the tenant or account you
					just authorized. Future connections will auto-fill this
					mapping's entity ID from the same field.
				</p>
			</div>

			<fieldset disabled={isPending} className="min-w-0 max-h-80 overflow-y-auto space-y-2 p-1">
				<legend className="sr-only">Entity ID source</legend>
				{candidates.map((c) => {
					const isSelected = selectedKey === keyId(c);
					return (
						<label
							key={keyId(c)}
							className={`flex min-h-11 w-full items-start gap-3 text-left rounded-[var(--bf-radius-control)] border p-4 cursor-pointer transition-colors motion-reduce:transition-none has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring has-[:disabled]:cursor-wait has-[:disabled]:opacity-60 ${
								isSelected
									? "border-primary bg-primary/5"
									: "hover:bg-muted/30"
							}`}
						>
							<input type="radio" name={groupName} checked={isSelected} onChange={() => setSelectedKey(keyId(c))} className="mt-0.5 size-4 shrink-0 accent-primary" />
							<div className="min-w-0 space-y-2">
								<div className="flex flex-wrap items-center gap-2 min-w-0">
									<span className="font-mono text-sm [overflow-wrap:anywhere]">
										{c.key}
									</span>
									<Badge
										variant="outline"
										className="text-xs"
									>
										{c.type}
									</Badge>
								</div>
								<div
									className="font-mono text-sm text-muted-foreground [overflow-wrap:anywhere]"
								>
									{c.value}
								</div>
							</div>
						</label>
					);
				})}
			</fieldset>

			{error && <p role="alert" className="text-sm text-destructive [overflow-wrap:anywhere]">{error}</p>}
			<div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
				<Button type="button" className="min-h-11" variant="outline" onClick={onSkip} disabled={isPending}>
					Skip
				</Button>
				<Button
					type="button"
					className="min-h-11"
					onClick={() => selected && onSelect(selected)}
					disabled={!selected || isPending}
				>
					{isPending ? "Saving…" : "Use this field"}
				</Button>
			</div>
		</div>
	);
}
