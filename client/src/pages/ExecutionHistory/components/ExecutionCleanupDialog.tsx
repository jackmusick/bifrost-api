import { useRef, useState } from "react";
import { CheckCircle, Eraser, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { apiClient } from "@/lib/api-client";
import { formatDate } from "@/lib/utils";
import { RunStatusBadge } from "@/components/execution";
import { Button } from "@/components/ui/button";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
	DialogTrigger,
} from "@/components/ui/dialog";

type StuckExecution = {
	execution_id: string;
	workflow_name: string;
	executed_by_name: string;
	status: string;
	started_at?: string | null;
};

export function ExecutionCleanupDialog({
	onCleaned,
}: {
	onCleaned: () => void;
}) {
	const [open, setOpen] = useState(false);
	const [executions, setExecutions] = useState<StuckExecution[]>([]);
	const [loading, setLoading] = useState(false);
	const [saving, setSaving] = useState(false);
	const [readError, setReadError] = useState(false);
	const [saveError, setSaveError] = useState(false);
	const pending = useRef(false);
	const readVersion = useRef(0);

	async function load() {
		const version = ++readVersion.current;
		setLoading(true);
		setReadError(false);
		try {
			const result = await apiClient.GET("/api/executions/cleanup/stuck");
			if (result.error || !result.data) throw new Error("Read failed");
			if (version === readVersion.current)
				setExecutions(result.data.executions || []);
		} catch {
			if (version === readVersion.current) setReadError(true);
		} finally {
			if (version === readVersion.current) setLoading(false);
		}
	}
	function changeOpen(next: boolean) {
		if (pending.current) return;
		setOpen(next);
		if (next) {
			setExecutions([]);
			setSaveError(false);
			void load();
		} else {
			readVersion.current++;
		}
	}
	async function clean() {
		if (pending.current || loading || readError || !executions.length)
			return;
		pending.current = true;
		setSaving(true);
		setSaveError(false);
		try {
			const result = await apiClient.POST(
				"/api/executions/cleanup/trigger",
				{},
			);
			if (result.error || !result.data) throw new Error("Cleanup failed");
			toast.success(`Cleaned up ${result.data.cleaned} stuck executions`);
			setOpen(false);
			onCleaned();
		} catch {
			setSaveError(true);
		} finally {
			pending.current = false;
			setSaving(false);
		}
	}
	return (
		<Dialog open={open} onOpenChange={changeOpen}>
			<DialogTrigger asChild>
				<Button
					variant="outline"
					size="icon-lg"
					aria-label="Cleanup stuck executions"
				>
					<Eraser className="size-4" />
				</Button>
			</DialogTrigger>
			<DialogContent
				className="flex max-h-[90dvh] max-w-3xl flex-col overflow-hidden"
				onEscapeKeyDown={(event) => {
					if (pending.current) event.preventDefault();
				}}
				onPointerDownOutside={(event) => {
					if (pending.current) event.preventDefault();
				}}
			>
				<DialogHeader className="shrink-0">
					<DialogTitle>Cleanup stuck executions</DialogTitle>
					<DialogDescription>
						Cleanup marks pending, running, or cancelling runs started over 24 hours ago as failed or cancelled.
					</DialogDescription>
				</DialogHeader>
				{saveError && (
					<p
						role="alert"
						className="shrink-0 text-sm text-destructive"
					>
						Could not clean up these executions. Review the list and
						retry.
					</p>
				)}
				<div className="min-h-0 overflow-y-auto">
					{loading ? (
						<div
							role="status"
							className="flex items-center justify-center gap-2 py-10 text-sm"
						>
							<Loader2 className="size-5 animate-spin motion-reduce:animate-none" />
							Loading stuck executions…
						</div>
					) : readError ? (
						<div role="alert" className="space-y-3 py-6 text-sm">
							<p>Could not load stuck executions.</p>
							<Button
								variant="outline"
								className="min-h-11"
								onClick={() => void load()}
							>
								Retry loading
							</Button>
						</div>
					) : !executions.length ? (
						<div className="flex flex-col items-center gap-3 py-10 text-center">
							<CheckCircle className="size-10 text-[var(--bf-success)]" />
							<h3 className="font-semibold">
								No stuck executions
							</h3>
							<p className="text-sm text-muted-foreground">
								All executions are running normally.
							</p>
						</div>
					) : (
						<ul
							aria-label="Stuck executions"
							className="divide-y rounded-[var(--bf-radius-surface)] border px-4"
						>
							{executions.map((execution) => (
								<li
									key={execution.execution_id}
									className="space-y-3 py-4"
								>
									<div className="flex flex-col items-start justify-between gap-2 sm:flex-row">
										<p className="min-w-0 flex-1 font-mono text-sm font-medium [overflow-wrap:anywhere]">
											{execution.workflow_name}
										</p>
										<RunStatusBadge
											status={execution.status}
										/>
									</div>
									<dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm sm:grid-cols-[auto_minmax(0,1fr)_auto_minmax(0,1fr)]">
										<dt className="text-muted-foreground">
											Run by
										</dt>
										<dd className="[overflow-wrap:anywhere]">
											{execution.executed_by_name}
										</dd>
										<dt className="text-muted-foreground">
											Started
										</dt>
										<dd className="[overflow-wrap:anywhere]">
											{execution.started_at
												? formatDate(
														execution.started_at,
													)
												: "Not started"}
										</dd>
									</dl>
								</li>
							))}
						</ul>
					)}
				</div>
				<DialogFooter className="shrink-0">
					<Button
						variant="outline"
						className="min-h-11"
						disabled={saving}
						onClick={() => changeOpen(false)}
					>
						Cancel
					</Button>
					<Button
						className="min-h-11 whitespace-normal"
						disabled={
							saving || loading || readError || !executions.length
						}
						onClick={() => void clean()}
					>
						{saving ? (
							<>
								<Loader2 className="size-4 animate-spin motion-reduce:animate-none" />
								Cleaning up…
							</>
						) : saveError ? (
							"Retry cleanup"
						) : (
							`Cleanup ${executions.length} execution${executions.length === 1 ? "" : "s"}`
						)}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
