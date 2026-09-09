import { useEffect, useRef, useState } from "react";
import { Loader2, XCircle } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { cancelExecution } from "@/hooks/useExecutions";
import { Button } from "@/components/ui/button";
import {
	AlertDialog,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";

interface Props {
	executionId: string;
	workflowName: string;
	status: string;
	scheduledAt?: string | null;
	compact?: boolean;
	onCancelled: (scheduled: boolean) => void;
	onRefresh: () => void;
}

export function ExecutionCancelAction({
	executionId,
	workflowName,
	status,
	scheduledAt,
	compact = false,
	onCancelled,
	onRefresh,
}: Props) {
	const [open, setOpen] = useState(false);
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const busy = useRef(false);
	const errorRef = useRef<HTMLParagraphElement>(null);
	useEffect(() => {
		if (error) errorRef.current?.focus();
	}, [error]);
	const scheduled = status === "Scheduled";
	const cancellable = ["Scheduled", "Pending", "Running"].includes(status);
	async function cancel() {
		if (busy.current || !cancellable) return;
		busy.current = true;
		setPending(true);
		setError(null);
		try {
			if (scheduled) {
				const result = await apiClient.POST(
					"/api/workflows/executions/{execution_id}/cancel",
					{ params: { path: { execution_id: executionId } } },
				);
				if (result.response?.status === 409) {
					setError(
						"This run has changed status. The list is refreshing; review its current status before trying again.",
					);
					toast.error("Execution changed status — refreshing");
					setOpen(false);
					onRefresh();
					return;
				}
				if (result.error || (result.response && !result.response.ok))
					throw new Error("Cancellation failed");
			} else await cancelExecution(executionId);
			setOpen(false);
			toast.success(
				scheduled
					? `Cancelled scheduled run of ${workflowName}`
					: `Cancellation requested for ${workflowName}`,
			);
			onCancelled(scheduled);
		} catch {
			setError("Could not cancel this execution. Please retry.");
		} finally {
			busy.current = false;
			setPending(false);
		}
	}
	const label = scheduled ? "Cancel scheduled execution" : "Cancel execution";
	return (
		<div
			className="min-w-0 space-y-2"
			onClick={(event) => event.stopPropagation()}
		>
			{cancellable && (
				<Button
					variant="outline"
					size={compact && !error ? "icon-lg" : "default"}
					className={compact && !error ? "min-h-11 whitespace-normal lg:size-8 lg:min-h-8" : "min-h-11 whitespace-normal"}
					title={label}
					aria-label={
						pending
							? "Cancelling execution"
							: error && !scheduled
								? "Retry cancellation"
								: label
					}
					disabled={pending}
					onClick={() => (scheduled ? setOpen(true) : void cancel())}
				>
					{pending ? (
						<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
					) : (
						<XCircle className="size-4" />
					)}
					{(!compact || error) &&
						(pending
							? "Cancelling…"
							: error && !scheduled
								? "Retry cancellation"
								: label)}
				</Button>
			)}
			{error && !open && (
				<p
					role="alert"
					ref={errorRef}
					tabIndex={-1}
					className="max-w-sm whitespace-normal text-left text-sm text-destructive [overflow-wrap:anywhere]"
				>
					{error}
				</p>
			)}
			<AlertDialog
				open={open}
				onOpenChange={(next) => {
					if (!busy.current) setOpen(next);
				}}
			>
				<AlertDialogContent
					className="flex max-h-[90dvh] flex-col overflow-hidden"
					onEscapeKeyDown={(event) => {
						if (busy.current) event.preventDefault();
					}}
				>
					<AlertDialogHeader className="min-h-0 overflow-y-auto">
						<AlertDialogTitle>
							Cancel scheduled run?
						</AlertDialogTitle>
						<AlertDialogDescription className="[overflow-wrap:anywhere]">
							Cancel scheduled run of{" "}
							<span className="font-mono">{workflowName}</span>
							{scheduledAt
								? ` for ${new Date(scheduledAt).toLocaleString()}`
								: ""}
							? The workflow will not run.
						</AlertDialogDescription>
					</AlertDialogHeader>
					{error && (
						<p
							role="alert"
							ref={errorRef}
							tabIndex={-1}
							className="shrink-0 text-sm text-destructive"
						>
							{error}
						</p>
					)}
					<AlertDialogFooter className="shrink-0">
						<Button
							variant="outline"
							className="min-h-11"
							disabled={pending}
							onClick={() => setOpen(false)}
						>
							Keep scheduled
						</Button>
						<Button
							variant="destructive"
							className="min-h-11"
							disabled={pending}
							onClick={() => void cancel()}
						>
							{pending
								? "Cancelling…"
								: error
									? "Retry cancellation"
									: "Confirm cancel"}
						</Button>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
