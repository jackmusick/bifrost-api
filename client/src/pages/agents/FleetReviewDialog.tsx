import { Link } from "react-router-dom";
import { useAgents } from "@/hooks/useAgents";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { FleetReadError } from "./FleetReadError";

/** Mounted only while open; reads all accessible agents, including paused ones. */
export function FleetReviewDialog({ onClose }: { onClose: () => void }) {
	const returnFocus = useDialogReturnFocus();
	const { data, isLoading, isError, isFetching, refetch } = useAgents(
		undefined,
		{ includeInactive: true, includeStats: true },
	);
	const queued = (data ?? [])
		.filter((agent) => (agent.stats?.needs_review ?? 0) > 0)
		.sort(
			(a, b) =>
				(b.stats?.needs_review ?? 0) - (a.stats?.needs_review ?? 0),
		);
	return (
		<Dialog
			open
			onOpenChange={(open) => {
				if (!open) onClose();
			}}
		>
			<DialogContent
				{...returnFocus}
				className="max-h-[90dvh] overflow-y-auto"
			>
				<DialogHeader>
					<DialogTitle>Review flagged runs</DialogTitle>
					<DialogDescription>
						Choose an agent to open its review queue. Includes
						paused agents you can access.
					</DialogDescription>
				</DialogHeader>
				{isError && (
					<FleetReadError
						resource="review queues"
						cached={!!data}
						pending={isFetching}
						onRetry={() => void refetch()}
					/>
				)}
				{isLoading ? (
					<p
						role="status"
						className="py-4 text-sm text-muted-foreground"
					>
						Loading review queues…
					</p>
				) : queued.length ? (
					<ul className="divide-y">
						{queued.map((agent) => (
							<li key={agent.id}>
								<Link
									to={`/agents/${agent.id}/review`}
									onClick={onClose}
									className="flex min-h-11 items-center justify-between gap-4 rounded-[var(--bf-radius-control)] px-2 py-3 text-sm transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none"
								>
									<span className="min-w-0 font-medium [overflow-wrap:anywhere]">
										{agent.name}
										{!agent.is_active && (
											<span className="mt-1 block text-xs font-normal text-muted-foreground">
												Paused
											</span>
										)}
									</span>
									<span className="shrink-0 text-muted-foreground">
										{agent.stats?.needs_review} flagged
									</span>
								</Link>
							</li>
						))}
					</ul>
				) : (
					!isError && (
						<p className="py-4 text-sm text-muted-foreground">
							No flagged runs are waiting for review.
						</p>
					)
				)}
			</DialogContent>
		</Dialog>
	);
}
