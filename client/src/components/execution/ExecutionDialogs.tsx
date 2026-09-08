import { Loader2 } from "lucide-react";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface ExecutionCancelDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	workflowName: string;
	onConfirm: () => void;
	isCancelling?: boolean;
	error?: string;
}

export function ExecutionCancelDialog({
	open,
	onOpenChange,
	workflowName,
	onConfirm,
	isCancelling,
	error,
}: ExecutionCancelDialogProps) {
	return (
		<AlertDialog open={open} onOpenChange={(next) => { if (!isCancelling) onOpenChange(next); }}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>Cancel Execution?</AlertDialogTitle>
					<AlertDialogDescription>
						Are you sure you want to cancel the execution of{" "}
						<span className="font-semibold [overflow-wrap:anywhere]">
							{workflowName}
						</span>
						? This action cannot be undone.
					</AlertDialogDescription>
				</AlertDialogHeader>
				{error && <p role="alert" className="text-sm text-destructive">{error}</p>}
				<AlertDialogFooter className="[&_button]:min-h-11 [&_button]:whitespace-normal">
					<AlertDialogCancel disabled={isCancelling}>No, keep running</AlertDialogCancel>
					<AlertDialogAction
						onClick={(event) => { if (isCancelling !== undefined) event.preventDefault(); onConfirm(); }}
						disabled={isCancelling}
						className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
					>
						{isCancelling ? "Requesting cancellation…" : error ? "Retry cancellation" : "Yes, cancel execution"}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}

interface ExecutionRerunDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	workflowName: string;
	isRerunning: boolean;
	onConfirm: () => void;
	error?: string;
}

export function ExecutionRerunDialog({
	open,
	onOpenChange,
	workflowName,
	isRerunning,
	onConfirm,
	error,
}: ExecutionRerunDialogProps) {
	return (
		<AlertDialog open={open} onOpenChange={(next) => { if (!isRerunning) onOpenChange(next); }}>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>Rerun Workflow?</AlertDialogTitle>
					<AlertDialogDescription>
						This will execute{" "}
						<span className="font-semibold [overflow-wrap:anywhere]">
							{workflowName}
						</span>{" "}
						again with the same input parameters. You will be
						redirected to the new execution.
					</AlertDialogDescription>
				</AlertDialogHeader>
				{error && <p role="alert" className="text-sm text-destructive">{error}</p>}
				<AlertDialogFooter className="[&_button]:min-h-11 [&_button]:whitespace-normal">
					<AlertDialogCancel disabled={isRerunning}>
						Cancel
					</AlertDialogCancel>
					<AlertDialogAction
						onClick={(event) => { event.preventDefault(); onConfirm(); }}
						disabled={isRerunning}
					>
						{isRerunning ? (
							<>
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
								Rerunning...
							</>
						) : (
							error ? "Retry rerun" : "Yes, rerun workflow"
						)}
					</AlertDialogAction>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
