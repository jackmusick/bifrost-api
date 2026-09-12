import type { RefObject } from "react";
import {
	Dialog,
	DialogContent,
	DialogClose,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SafeHTMLRenderer } from "@/components/execution/SafeHTMLRenderer";

interface TerminalResultModalProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	html: string;
	executionId: string;
	returnFocusRef?: RefObject<HTMLElement | null>;
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
	returnFocusRef,
}: TerminalResultModalProps) {
	return (
		<Dialog open={open} onOpenChange={onOpenChange}>
			<DialogContent onCloseAutoFocus={(event) => { if (returnFocusRef?.current) { event.preventDefault(); returnFocusRef.current.focus(); } }} showCloseButton={false} className="flex h-[90dvh] max-h-[90dvh] max-w-4xl flex-col gap-4 overflow-hidden p-4 sm:p-6">
				<div className="flex shrink-0 items-start justify-between gap-3">
					<DialogHeader>
						<DialogTitle className="font-display text-xl">Execution result</DialogTitle>
						<DialogDescription>HTML output from run {executionId.slice(0, 8)}.</DialogDescription>
					</DialogHeader>
					<DialogClose asChild><Button variant="outline" size="icon-lg" className="shrink-0" aria-label="Close execution result"><X aria-hidden="true" className="size-4" /></Button></DialogClose>
				</div>
				<div className="min-h-0 min-w-0 flex-1">
					<SafeHTMLRenderer
						html={html}
						className="flex h-full min-h-0 flex-col gap-3 space-y-0 [&>iframe]:min-h-0 [&>iframe]:flex-1 [&>iframe]:h-auto"
						title={`Execution ${executionId.slice(0, 8)} - Result`}
					/>
				</div>
			</DialogContent>
		</Dialog>
	);
}
