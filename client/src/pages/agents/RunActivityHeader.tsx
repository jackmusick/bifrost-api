import { cn } from "@/lib/utils";
import { Code2, ListTree } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export function RunActivityHeader({
	advanced,
	onChange,
	className,
}: {
	advanced: boolean;
	onChange: (value: boolean) => void;
	className?: string;
}) {
	return (
		<CardHeader
			className={cn(
				"flex w-full min-w-0 flex-col gap-3 border-b px-5 pb-4 sm:flex-row sm:items-start sm:justify-between",
				className,
			)}
		>
			<div className="min-w-0 space-y-1">
				<CardTitle className="flex items-center gap-2 text-sm">
					<ListTree
						aria-hidden="true"
						className="size-4 text-muted-foreground"
					/>
					Activity
				</CardTitle>
				<CardDescription className="text-xs">
					How the agent handled this run, in order
				</CardDescription>
			</div>
			<div
				role="group"
				aria-label="Activity detail level"
				className="flex w-full gap-1 rounded-[var(--bf-radius-control)] border bg-muted p-1 sm:w-auto"
			>
				<Button
					type="button"
					variant={advanced ? "ghost" : "secondary"}
					aria-pressed={!advanced}
					onClick={() => onChange(false)}
					className="min-h-11 flex-1 sm:flex-none"
				>
					Activity
				</Button>
				<Button
					type="button"
					variant={advanced ? "secondary" : "ghost"}
					aria-pressed={advanced}
					onClick={() => onChange(true)}
					className="min-h-11 flex-1 sm:flex-none"
				>
					<Code2 aria-hidden="true" className="size-4" />
					Advanced
				</Button>
			</div>
		</CardHeader>
	);
}
