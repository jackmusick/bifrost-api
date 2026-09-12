import { ThumbsUp, ThumbsDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type Verdict = "up" | "down" | null;

export interface VerdictToggleProps {
	value: Verdict;
	onChange: (v: Verdict) => void;
	disabled?: boolean;
	size?: "sm" | "md";
	className?: string;
}

export function VerdictToggle({
	value,
	onChange,
	disabled,
	size = "md",
	className,
}: VerdictToggleProps) {
	function toggle(target: "up" | "down") {
		if (disabled) return;
		onChange(value === target ? null : target);
	}

	const dim = size === "sm" ? 28 : 32;
	const iconSize = size === "sm" ? 14 : 16;

	return (
		<div
			className={cn("inline-flex gap-1.5", className)}
			role="group"
			aria-label="Verdict"
		>
			<button
				type="button"
				aria-label="Mark as good"
				aria-pressed={value === "up"}
				disabled={disabled}
				onClick={() => toggle("up")}
				className={cn(
					"grid min-h-11 min-w-11 place-items-center rounded-[var(--bf-radius-control)] border transition-colors duration-[var(--bf-motion-feedback)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none sm:min-h-0 sm:min-w-0",

					value === "up"
						? "bg-[var(--bf-success-soft)] border-[var(--bf-success)] text-[var(--bf-success)]"
						: "bg-background border-border text-muted-foreground hover:text-foreground",
					disabled && "opacity-50 cursor-not-allowed",
				)}
				style={{ width: dim, height: dim }}
			>
				<ThumbsUp size={iconSize} />
			</button>
			<button
				type="button"
				aria-label="Mark as bad"
				aria-pressed={value === "down"}
				disabled={disabled}
				onClick={() => toggle("down")}
				className={cn(
					"grid min-h-11 min-w-11 place-items-center rounded-[var(--bf-radius-control)] border transition-colors duration-[var(--bf-motion-feedback)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none sm:min-h-0 sm:min-w-0",

					value === "down"
						? "bg-[var(--bf-danger-soft)] border-[var(--bf-danger)] text-[var(--bf-danger)]"
						: "bg-background border-border text-muted-foreground hover:text-foreground",
					disabled && "opacity-50 cursor-not-allowed",
				)}
				style={{ width: dim, height: dim }}
			>
				<ThumbsDown size={iconSize} />
			</button>
		</div>
	);
}
