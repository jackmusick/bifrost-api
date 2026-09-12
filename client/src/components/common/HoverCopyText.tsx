import { useEffect, useState } from "react";
import { Check, Copy } from "lucide-react";
import { toast } from "sonner";

import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import { copyToClipboard } from "@/lib/clipboard";
import { cn } from "@/lib/utils";

interface HoverCopyTextProps {
	value: string;
	label?: string;
	className?: string;
}

export function HoverCopyText({
	value,
	label = "text",
	className,
}: HoverCopyTextProps) {
	const [open, setOpen] = useState(false);
	const [copyState, setCopyState] = useState<"idle" | "pending" | "copied">(
		"idle",
	);

	useEffect(() => {
		if (copyState !== "copied") return;
		const timeout = window.setTimeout(() => setCopyState("idle"), 1600);
		return () => window.clearTimeout(timeout);
	}, [copyState]);

	const handleCopy = async () => {
		if (copyState === "pending") return;
		setCopyState("pending");
		const copied = await copyToClipboard(value);
		setCopyState(copied ? "copied" : "idle");
		if (copied) {
			setOpen(true);
			toast.success(`${label} copied`);
		} else toast.error(`Failed to copy ${label.toLowerCase()}`);
	};

	const copied = copyState === "copied";

	return (
		<Popover open={open} onOpenChange={setOpen}>
			<PopoverTrigger asChild>
				<button
					type="button"
					className={cn(
						"group min-w-0 cursor-copy rounded-[var(--bf-radius-control)] text-left font-mono text-xs leading-6 text-foreground [overflow-wrap:anywhere] transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none",
						className,
					)}
					onMouseEnter={() => setOpen(true)}
					onMouseLeave={() => setOpen(false)}
					onFocus={() => setOpen(true)}
					onBlur={() => setOpen(false)}
					onClick={() => void handleCopy()}
					aria-label={copied ? `${label} copied` : `Copy ${label}`}
				>
					{value}
				</button>
			</PopoverTrigger>
			<PopoverContent
				side="top"
				align="start"
				onOpenAutoFocus={(event) => event.preventDefault()}
				onCloseAutoFocus={(event) => event.preventDefault()}
				className="w-auto max-w-[calc(100vw-2rem)] px-2 py-1"
			>
				<span className="inline-flex items-center gap-1 text-xs">
					{copied ? (
						<Check
							aria-hidden="true"
							className="size-3 text-[var(--bf-success)]"
						/>
					) : (
						<Copy aria-hidden="true" className="size-3" />
					)}
					{copied ? "Copied" : "Copy"}
				</span>
			</PopoverContent>
		</Popover>
	);
}
