import { useState } from "react";
import { Check, ChevronDown, ChevronRight, Loader2 } from "lucide-react";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "@/components/ui/collapsible";
import type { FileChange } from "@/hooks/useGitHub";

interface ChangesListProps {
	changes: FileChange[];
	hasConflicts: boolean;
	onFileClick: (file: FileChange) => void;
	isLoading?: boolean;
}

export function ChangesList({
	changes,
	hasConflicts,
	onFileClick,
	isLoading = false,
}: ChangesListProps) {
	const [isOpen, setIsOpen] = useState(true);

	const getStatusIcon = (status: string) => {
		switch (status) {
			case "M":
				return <span className="text-[var(--bf-info)]">M</span>;
			case "A":
				return <span className="text-[var(--bf-success)]">A</span>;
			case "D":
				return <span className="text-[var(--bf-danger)]">D</span>;
			case "U":
				return <span className="text-[var(--bf-warning)]">U</span>;
			case "C":
				return <span className="text-[var(--bf-warning)]">C</span>;
			default:
				return <span className="text-muted-foreground">?</span>;
		}
	};

	return (
		<Collapsible
			open={isOpen}
			onOpenChange={setIsOpen}
			className="flex min-w-0 flex-col min-h-0"
		>
			<CollapsibleTrigger
				type="button"
				className="min-h-11 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring motion-reduce:transition-none flex items-center justify-between w-full px-4 py-2 hover:bg-muted/50 transition-colors border-b flex-shrink-0"
			>
				<div className="flex items-center gap-2">
					{isOpen ? (
						<ChevronDown className="h-4 w-4" />
					) : (
						<ChevronRight className="h-4 w-4" />
					)}
					<span className="text-sm font-medium">
						Changes ({changes.length})
					</span>
				</div>
			</CollapsibleTrigger>
			<CollapsibleContent className="flex-1 min-h-0">
				<div className="h-full overflow-y-auto px-4 py-2">
					{isLoading ? (
						<div
							role="status"
							className="flex flex-col items-center justify-center py-8 text-center"
						>
							<Loader2 className="h-6 w-6 text-muted-foreground mb-2 motion-safe:animate-spin" />
							<p className="text-sm text-muted-foreground">
								Loading changes...
							</p>
						</div>
					) : changes.length === 0 && !hasConflicts ? (
						<div
							role="status"
							className="flex flex-col items-center justify-center py-8 text-center"
						>
							<Check className="h-6 w-6 text-[var(--bf-success)] mb-2" />
							<p className="text-sm text-muted-foreground">
								No changes
							</p>
						</div>
					) : (
						<div className="space-y-1">
							{changes.map((file) => (
								<button
									key={file.path}
									type="button"
									onClick={() => onFileClick(file)}
									className="grid grid-cols-[auto_minmax(0,1fr)] min-h-11 min-w-0 items-start gap-x-2 gap-y-1 w-full px-2 py-3 rounded-[var(--bf-radius-control)] text-sm leading-5 hover:bg-muted/50 transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
								>
									{getStatusIcon(file.status)}
									<span className="min-w-0 text-left flex-1 font-mono [overflow-wrap:anywhere]">
										{file.path}
									</span>
									{file.additions !== null &&
										file.deletions !== null && (
											<span className="col-start-2 text-left text-muted-foreground text-xs tabular-nums">
												+{file.additions} -
												{file.deletions}
											</span>
										)}
								</button>
							))}
						</div>
					)}
				</div>
			</CollapsibleContent>
		</Collapsible>
	);
}
