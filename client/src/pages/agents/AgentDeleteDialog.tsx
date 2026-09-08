import { useRef, useState } from "react";
import { useDeleteAgent } from "@/hooks/useAgents";
import {
	AlertDialog,
	AlertDialogContent,
	AlertDialogHeader,
	AlertDialogTitle,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogCancel,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";

export function AgentDeleteDialog({
	agentId,
	name,
	open,
	onOpenChange,
	onDeleted,
}: {
	agentId: string;
	name: string;
	open: boolean;
	onOpenChange: (open: boolean) => void;
	onDeleted: () => void;
}) {
	const mutation = useDeleteAgent();
	const busy = useRef(false);
	const [failed, setFailed] = useState(false);
	async function remove() {
		if (busy.current) return;
		busy.current = true;
		setFailed(false);
		try {
			await mutation.mutateAsync({
				params: { path: { agent_id: agentId } },
			});
			onOpenChange(false);
			onDeleted();
		} catch {
			setFailed(true);
		} finally {
			busy.current = false;
		}
	}
	return (
		<AlertDialog
			open={open}
			onOpenChange={(next) => {
				if (busy.current) return;
				setFailed(false);
				onOpenChange(next);
			}}
		>
			<AlertDialogContent>
				<AlertDialogHeader>
					<AlertDialogTitle>Delete agent?</AlertDialogTitle>
					<AlertDialogDescription>
						This will delete{" "}
						<strong className="[overflow-wrap:anywhere]">
							{name}
						</strong>{" "}
						and its run history. This action cannot be undone.
					</AlertDialogDescription>
				</AlertDialogHeader>
				{failed ? (
					<p
						role="alert"
						className="rounded-[var(--bf-radius-control)] border bg-[var(--bf-warning-soft)] p-3 text-sm"
					>
						Could not delete the agent. Try again.
					</p>
				) : null}
				{mutation.isPending ? (
					<p role="status" className="text-sm text-muted-foreground">
						Deleting agent…
					</p>
				) : null}
				<AlertDialogFooter>
					<AlertDialogCancel
						className="min-h-11 lg:min-h-11"
						disabled={mutation.isPending}
					>
						Cancel
					</AlertDialogCancel>
					<Button
						variant="destructive"
						className="min-h-11 lg:min-h-11"
						disabled={mutation.isPending}
						onClick={() => void remove()}
					>
						{failed ? "Retry delete" : "Delete"}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
