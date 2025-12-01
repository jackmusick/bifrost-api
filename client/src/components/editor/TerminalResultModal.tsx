import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { SafeHTMLRenderer } from "@/components/execution/SafeHTMLRenderer";

interface TerminalResultModalProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	html: string;
	executionId: string;
}

/**
 * Modal for displaying HTML execution results from the terminal
 * Reuses SafeHTMLRenderer for safe HTML rendering
 */
export function TerminalResultModal({
	open,
	onOpenChange,
	html,
	executionId,
}: TerminalResultModalProps) {
	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent className="max-w-4xl max-h-[80vh] overflow-hidden flex flex-col">
				<DialogHeader>
					<DialogTitle>Execution Result</DialogTitle>
				</DialogHeader>
				<div className="flex-1 overflow-auto">
					<SafeHTMLRenderer
						html={html}
						title={`Execution ${executionId.slice(0, 8)} - Result`}
					/>
				</div>
			</DialogContent>
		</Dialog>
	);
}
