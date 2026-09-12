import { ExternalLink, X } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { ExecutionDetails } from "@/pages/ExecutionDetails";

interface ExecutionPreviewPanelProps {
	executionId: string | null;
	onClose: () => void;
	onExecutionChange?: (newExecutionId: string) => void;
}

export function ExecutionPreviewPanel({
	executionId,
	onClose,
	onExecutionChange,
}: ExecutionPreviewPanelProps) {
	if (!executionId) {
		return null;
	}

	return (
		<aside
			className="hidden min-h-0 rounded-[var(--bf-radius-surface)] border border-border bg-card lg:flex lg:flex-col"
			aria-label="Execution preview"
			data-testid="execution-preview-panel"
		>
			<div className="sticky top-0 z-10 border-b border-border bg-card px-3 py-2.5">
				<div className="flex items-center justify-between gap-3">
					<div className="min-w-0">
						<h2 className="truncate text-sm font-semibold">
							Execution preview
						</h2>
						<p className="truncate font-mono text-xs text-muted-foreground">
							{executionId}
						</p>
					</div>
					<div className="flex shrink-0 items-center gap-1">
						<Button
							variant="ghost"
							size="sm"
							className="gap-1.5 px-2"
							asChild
						>
							<Link
								to={`/history/${executionId}`}
								aria-label="Open execution"
								title="Open execution"
							>
								<ExternalLink className="h-4 w-4" />
								<span className="hidden 2xl:inline">
									Open execution
								</span>
							</Link>
						</Button>
						<Button
							variant="ghost"
							size="sm"
							className="gap-1.5 px-2"
							onClick={onClose}
							aria-label="Close execution preview"
							title="Close execution preview"
						>
							<X className="h-4 w-4" />
							<span className="hidden 2xl:inline">Close</span>
						</Button>
					</div>
				</div>
			</div>
			<div className="min-h-0 flex-1 overflow-y-auto p-4">
				<ExecutionDetails
					executionId={executionId}
					embedded
					onExecutionChange={onExecutionChange}
				/>
			</div>
		</aside>
	);
}
