import { ChevronRight, ChevronDown, Copy, Check } from "lucide-react";
import { useId, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { copyToClipboard } from "@/lib/clipboard";

interface VariablesTreeViewProps {
	data: Record<string, unknown>;
}

/** Expandable variable inspector with wrapping values and keyboard-accessible actions. */
export function VariablesTreeView({ data }: VariablesTreeViewProps) {
	return (
		<div className="min-w-0 divide-y divide-border/60 font-mono text-xs leading-relaxed">
			{Object.entries(data).map(([name, value]) => (
				<VariableItem key={name} name={name} value={value} depth={0} />
			))}
		</div>
	);
}

interface VariableItemProps {
	name: string;
	value: unknown;
	depth: number;
}

function displayValue(value: unknown): string {
	if (value === null) return "null";
	if (value === undefined) return "undefined";
	if (typeof value === "string") return `"${value}"`;
	if (Array.isArray(value)) return `Array(${value.length})`;
	if (typeof value === "object") {
		const count = Object.keys(value).length;
		return `{${count} ${count === 1 ? "property" : "properties"}}`;
	}
	return String(value);
}

function VariableItem({ name, value, depth }: VariableItemProps) {
	const [isExpanded, setIsExpanded] = useState(false);
	const [copyState, setCopyState] = useState<"idle" | "pending" | "copied">(
		"idle",
	);
	const childrenId = useId();
	const isExpandable = value !== null && typeof value === "object";
	const entries = isExpandable
		? Array.isArray(value)
			? value.map((item, index) => [`[${index}]`, item] as const)
			: Object.entries(value)
		: [];

	const handleCopy = async () => {
		if (copyState === "pending") return;
		setCopyState("pending");
		const text = isExpandable
			? JSON.stringify(value, null, 2)
			: String(value);
		const success = await copyToClipboard(text);
		setCopyState(success ? "copied" : "idle");
		if (success) toast.success("Copied to clipboard");
		else toast.error("Failed to copy to clipboard");
	};

	const label = (
		<span className="min-w-0 whitespace-pre-wrap [overflow-wrap:anywhere]">
			<span className="font-medium text-primary">{name}: </span>
			<span
				className={
					isExpandable
						? "rounded bg-background/70 px-1.5 py-0.5 text-muted-foreground"
						: value == null
							? "italic text-muted-foreground"
							: typeof value === "number" ||
								  typeof value === "boolean"
								? "font-semibold text-foreground"
								: "text-foreground"
				}
			>
				{displayValue(value)}
			</span>
		</span>
	);

	return (
		<div className="min-w-0">
			<div
				className="group flex min-w-0 items-start gap-1 rounded-[var(--bf-radius-control)] transition-colors hover:bg-primary/5 focus-within:bg-primary/5 motion-reduce:transition-none"
				style={{ paddingLeft: `${Math.min(depth, 3) * 8}px` }}
			>
				{isExpandable ? (
					<button
						type="button"
						aria-expanded={isExpanded}
						aria-controls={childrenId}
						aria-label={`${isExpanded ? "Collapse" : "Expand"} ${name}`}
						onClick={() => setIsExpanded(!isExpanded)}
						className="flex min-h-11 min-w-0 flex-1 items-start gap-1 rounded-[var(--bf-radius-control)] px-1 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
					>
						{isExpanded ? (
							<ChevronDown className="mt-0.5 size-3 shrink-0" />
						) : (
							<ChevronRight className="mt-0.5 size-3 shrink-0" />
						)}
						{label}
					</button>
				) : (
					<div className="min-w-0 flex-1 px-1 py-3">{label}</div>
				)}
				<Button
					variant="ghost"
					size="icon-lg"
					className="shrink-0"
					aria-label={`Copy ${name} value`}
					title={copyState === "copied" ? "Copied" : "Copy value"}
					disabled={copyState === "pending"}
					onClick={handleCopy}
				>
					{copyState === "copied" ? (
						<Check className="size-3 text-[var(--bf-success)]" />
					) : (
						<Copy className="size-3 text-muted-foreground" />
					)}
				</Button>
			</div>
			{isExpandable && (
				<div
					id={childrenId}
					hidden={!isExpanded}
					className="ml-3 border-l border-border bg-background/40"
				>
					{isExpanded &&
						(entries.length ? (
							entries.map(([key, item]) => (
								<VariableItem
									key={key}
									name={key}
									value={item}
									depth={depth + 1}
								/>
							))
						) : (
							<p className="px-4 py-2 text-muted-foreground">
								{Array.isArray(value)
									? "Empty array"
									: "Empty object"}
							</p>
						))}
				</div>
			)}
		</div>
	);
}
