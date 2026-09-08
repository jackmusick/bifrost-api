import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ConflictInfo {
	current_content: string;
	incoming_content: string;
}

interface ConflictResolutionBannerProps {
	conflict: ConflictInfo;
	filePath: string;
	onResolve: (choice: "current" | "incoming" | "both") => void;
}

export function ConflictResolutionBanner({
	conflict,
	filePath,
	onResolve,
}: ConflictResolutionBannerProps) {
	if (!conflict) return null;

	return (
		<div
			role="region"
			aria-label="File merge conflict"
			className="min-w-0 border-b border-border bg-[var(--bf-warning-soft)] px-4 py-3"
		>
			<div className="flex min-w-0 flex-col gap-3 lg:flex-row lg:items-center">
				<div className="flex min-w-0 flex-1 items-start gap-2">
					<AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--bf-warning)]" />
					<div className="min-w-0 space-y-1">
						<p className="text-sm font-medium">
							This file has a merge conflict
						</p>
						<p className="font-mono text-sm leading-5 text-muted-foreground [overflow-wrap:anywhere]">
							{filePath}
						</p>
					</div>
				</div>
				<div className="flex flex-wrap items-center gap-2">
					<Button
						type="button"
						size="sm"
						variant="outline"
						onClick={() => onResolve("current")}
						className="min-h-11 h-auto whitespace-normal"
					>
						Keep my changes
					</Button>
					<Button
						type="button"
						size="sm"
						variant="outline"
						onClick={() => onResolve("incoming")}
						className="min-h-11 h-auto whitespace-normal"
					>
						Keep their changes
					</Button>
					<Button
						type="button"
						size="sm"
						variant="outline"
						onClick={() => onResolve("both")}
						className="min-h-11 h-auto whitespace-normal"
					>
						Keep both
					</Button>
				</div>
			</div>
		</div>
	);
}
