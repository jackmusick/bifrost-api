/**
 * OrphanedWorkflowDialog Component
 *
 * Dialog for managing orphaned workflows. Shows when a workflow's backing file
 * no longer exists. Provides options to:
 * - Replace with a compatible function from another file
 * - Recreate the file from the stored code snapshot
 * - Deactivate the workflow
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useReducedMotion } from "framer-motion";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
	AlertTriangle,
	FileCode,
	RefreshCw,
	XCircle,
	ArrowRightLeft,
	Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { authFetch } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import type { components } from "@/lib/v1";

// Type for workflow from the API
type Workflow = components["schemas"]["WorkflowMetadata"];

// Types for orphan management API (may not be in generated types yet)
interface WorkflowReference {
	type: "form" | "app" | "agent";
	id: string;
	name: string;
}

interface CompatibleReplacement {
	path: string;
	function_name: string;
	signature: string;
	compatibility: "exact" | "compatible";
}

interface OrphanedWorkflowDialogProps {
	/** Whether the dialog is open */
	open: boolean;
	/** Callback when dialog should close */
	onClose: () => void;
	/** The orphaned workflow to manage */
	workflow: Workflow;
	/** Callback after successful action (to refresh data) */
	onSuccess?: () => void;
}

/**
 * Dialog for resolving orphaned workflows.
 *
 * An orphaned workflow is one whose backing file has been deleted or no longer
 * contains the workflow function. The workflow continues to work using its
 * stored code snapshot, but cannot be edited via files.
 */
export function OrphanedWorkflowDialog({
	open,
	onClose,
	workflow,
	onSuccess,
}: OrphanedWorkflowDialogProps) {
	const prefersReducedMotion = useReducedMotion();
	const [replacements, setReplacements] = useState<CompatibleReplacement[]>(
		[],
	);
	const [usedBy, setUsedBy] = useState<WorkflowReference[]>([]);
	const [referencesLoading, setReferencesLoading] = useState(false);
	const [referencesError, setReferencesError] = useState(false);
	const referencesRequest = useRef(0);
	const [selectedReplacement, setSelectedReplacement] = useState<
		string | null
	>(null);
	const [isLoadingReplacements, setIsLoadingReplacements] = useState(false);
	const [isActionLoading, setIsActionLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const actionBusy = useRef(false);
	const [failedAction, setFailedAction] = useState<
		"replace" | "recreate" | "deactivate" | null
	>(null);
	const errorRef = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (error) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView?.({ block: "nearest" });
		}
	}, [error]);

	// Fetch compatible replacements when dialog opens
	const fetchReplacements = useCallback(async () => {
		if (!open || !workflow.id) return;

		setFailedAction(null);
		setIsLoadingReplacements(true);
		setError(null);

		try {
			const response = await authFetch(
				`/api/workflows/${workflow.id}/compatible-replacements`,
			);

			if (!response.ok) {
				throw new Error("Failed to fetch compatible replacements");
			}

			const data = await response.json();
			setReplacements(data.replacements || []);
		} catch (err) {
			console.error("Error fetching replacements:", err);
			setError("Failed to load compatible replacements");
		} finally {
			setIsLoadingReplacements(false);
		}
	}, [open, workflow.id]);

	// Fetch workflow references (what entities use this workflow)
	const fetchReferences = useCallback(async () => {
		if (!open || !workflow.id) return;
		const request = ++referencesRequest.current;
		setReferencesLoading(true);
		setReferencesError(false);
		try {
			const response = await authFetch(
				`/api/workflows/${workflow.id}/references`,
			);
			if (!response.ok) throw new Error("Could not load dependencies");
			const data = await response.json();
			if (request === referencesRequest.current)
				setUsedBy(data.references || []);
		} catch {
			if (request === referencesRequest.current) setReferencesError(true);
		} finally {
			if (request === referencesRequest.current)
				setReferencesLoading(false);
		}
	}, [open, workflow.id]);

	const handleRetry = useCallback(() => {
		void Promise.all([fetchReplacements(), fetchReferences()]);
	}, [fetchReplacements, fetchReferences]);

	// Reset state and load data when dialog opens. State is set inside the
	// async functions only after awaited fetches resolve — the rule fires on
	// synchronous setState in effects, which we avoid via the void-promise
	// kick-off. Reset of selectedReplacement is also wrapped so it does not
	// run synchronously within the effect body.
	useEffect(() => {
		if (!open) return;
		void (async () => {
			setSelectedReplacement(null);
			setUsedBy([]);
			await Promise.all([fetchReplacements(), fetchReferences()]);
		})();
	}, [open, fetchReplacements, fetchReferences]);

	// Handle replace action
	const handleReplace = async () => {
		if (!selectedReplacement || actionBusy.current) return;
		actionBusy.current = true;
		setFailedAction(null);

		setIsActionLoading(true);
		setError(null);

		try {
			const [path, funcName] = selectedReplacement.split("::");

			const response = await authFetch(
				`/api/workflows/${workflow.id}/replace`,
				{
					method: "POST",
					body: JSON.stringify({
						source_path: path,
						function_name: funcName,
					}),
				},
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(
					errorData.detail || "Failed to replace workflow",
				);
			}

			toast.success(`Workflow "${workflow.name}" replaced successfully`);
			onSuccess?.();
			onClose();
		} catch (err) {
			const message =
				err instanceof Error
					? err.message
					: "Failed to replace workflow";
			setFailedAction("replace");
			setError(message);
		} finally {
			actionBusy.current = false;
			setIsActionLoading(false);
		}
	};

	// Handle recreate file action
	const handleRecreate = async () => {
		if (actionBusy.current) return;
		actionBusy.current = true;
		setFailedAction(null);
		setIsActionLoading(true);
		setError(null);

		try {
			const response = await authFetch(
				`/api/workflows/${workflow.id}/recreate`,
				{
					method: "POST",
				},
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(errorData.detail || "Failed to recreate file");
			}

			toast.success(`File recreated for workflow "${workflow.name}"`);
			onSuccess?.();
			onClose();
		} catch (err) {
			const message =
				err instanceof Error ? err.message : "Failed to recreate file";
			setFailedAction("recreate");
			setError(message);
		} finally {
			actionBusy.current = false;
			setIsActionLoading(false);
		}
	};

	// Handle deactivate action
	const handleDeactivate = async () => {
		if (actionBusy.current) return;
		actionBusy.current = true;
		setFailedAction(null);
		setIsActionLoading(true);
		setError(null);

		try {
			const response = await authFetch(
				`/api/workflows/${workflow.id}/deactivate`,
				{
					method: "POST",
				},
			);

			if (!response.ok) {
				const errorData = await response.json().catch(() => ({}));
				throw new Error(
					errorData.detail || "Failed to deactivate workflow",
				);
			}

			const data = await response.json();
			if (data.warning) {
				toast.warning(data.warning);
			} else {
				toast.success(`Workflow "${workflow.name}" deactivated`);
			}
			onSuccess?.();
			onClose();
		} catch (err) {
			const message =
				err instanceof Error
					? err.message
					: "Failed to deactivate workflow";
			setFailedAction("deactivate");
			setError(message);
		} finally {
			actionBusy.current = false;
			setIsActionLoading(false);
		}
	};

	// Get the last known path from the workflow
	const lastPath =
		workflow.relative_file_path || workflow.source_file_path || "Unknown";

	return (
		<Dialog
			open={open}
			onOpenChange={(isOpen) => {
				if (!isOpen && !actionBusy.current) onClose();
			}}
		>
			<DialogContent className="max-h-[min(90dvh,52rem)] w-[min(calc(100vw-1rem),42rem)] overflow-hidden p-0 sm:max-w-none">
				<div className="flex max-h-[min(90dvh,52rem)] min-h-0 flex-col overflow-hidden">
					<div className="space-y-3 border-b border-border/70 bg-muted/20 p-4 sm:p-6">
						<DialogHeader>
							<DialogTitle className="flex items-center gap-2 text-left">
								<AlertTriangle className="h-5 w-5 shrink-0 text-[var(--bf-warning)]" />
								Orphaned Workflow
							</DialogTitle>
							<DialogDescription className="max-w-prose leading-6 [overflow-wrap:anywhere]">
								The source file is missing. Restore it, replace
								the workflow, or deactivate it.
							</DialogDescription>
						</DialogHeader>
					</div>

					<div className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6">
						<div className="space-y-4">
							<div className="grid gap-2 text-sm sm:grid-cols-2">
								<div className="rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-3">
									<div className="text-muted-foreground">
										Workflow
									</div>
									<div className="mt-1 font-medium [overflow-wrap:anywhere]">
										{workflow.name}
									</div>
								</div>
								<div className="rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-3">
									<div className="text-muted-foreground">
										Function
									</div>
									<code className="mt-1 block rounded bg-muted px-2 py-1 font-mono text-xs [overflow-wrap:anywhere]">
										{workflow.function_name ||
											workflow.name}
									</code>
								</div>
								<div className="rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-3 sm:col-span-2">
									<div className="text-muted-foreground">
										Last path
									</div>
									<code className="mt-1 block rounded bg-muted px-2 py-1 font-mono text-xs leading-5 [overflow-wrap:anywhere]">
										{lastPath}
									</code>
								</div>
								{(usedBy.length > 0 ||
									referencesLoading ||
									referencesError) && (
									<div className="rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-3 sm:col-span-2">
										<div className="text-muted-foreground">
											Used by
										</div>

										{referencesLoading && (
											<p
												role="status"
												className="mt-2 text-sm text-muted-foreground"
											>
												Loading dependencies…
											</p>
										)}
										{referencesError && (
											<div
												role="alert"
												className="mt-2 space-y-2 text-sm"
											>
												<p>
													Could not load dependencies.
													This workflow may still be
													in use.
												</p>
												<Button
													type="button"
													variant="outline"
													className="min-h-11"
													disabled={
														referencesLoading ||
														isActionLoading
													}
													onClick={() =>
														void fetchReferences()
													}
												>
													Retry dependencies
												</Button>
											</div>
										)}
										<div className="mt-2 flex flex-wrap gap-1.5">
											{usedBy.map((ref) => (
												<Badge
													key={`${ref.type}-${ref.id}`}
													variant="secondary"
													className="max-w-full whitespace-normal [overflow-wrap:anywhere]"
												>
													{ref.name}
												</Badge>
											))}
										</div>
									</div>
								)}
							</div>
							{error && (
								<div
									role="alert"
									ref={errorRef}
									tabIndex={-1}
									className="flex items-start justify-between gap-3 outline-none rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-3 text-sm leading-6 text-[var(--bf-danger)]"
								>
									<p className="min-w-0 flex-1 [overflow-wrap:anywhere]">
										{error}
									</p>
									<Button
										type="button"
										variant="outline"
										size="sm"
										className="min-h-11 shrink-0"
										onClick={() => {
											if (failedAction === "replace")
												void handleReplace();
											else if (
												failedAction === "recreate"
											)
												void handleRecreate();
											else if (
												failedAction === "deactivate"
											)
												void handleDeactivate();
											else handleRetry();
										}}
										disabled={
											isLoadingReplacements ||
											isActionLoading
										}
									>
										Retry
									</Button>
								</div>
							)}

							<div className="space-y-3 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4 shadow-sm">
								<div className="flex items-center gap-2">
									<ArrowRightLeft className="h-4 w-4 shrink-0 text-muted-foreground" />
									<h4 className="font-medium leading-6">
										Replace with existing file
									</h4>
								</div>
								<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
									Link this workflow to an existing function.
									Connected forms, apps, and agents will use
									the replacement.
								</p>

								{isLoadingReplacements ? (
									<div className="space-y-2">
										<Skeleton className="h-11 w-full rounded-[var(--bf-radius-control)]" />
									</div>
								) : replacements.length > 0 ? (
									<>
										<Select
											disabled={isActionLoading}
											value={selectedReplacement || ""}
											onValueChange={
												setSelectedReplacement
											}
										>
											<SelectTrigger aria-label="Replacement function" className="data-[size=default]:h-auto min-h-11 w-full whitespace-normal text-left *:data-[slot=select-value]:line-clamp-none *:data-[slot=select-value]:block">
												<SelectValue placeholder="Select a replacement..." className="min-w-0 flex-1">
													{selectedReplacement && (
														<span className="block space-y-1 font-mono text-xs leading-5 [overflow-wrap:anywhere]">
															<span className="block">{selectedReplacement.split("::")[0]}</span>
															<span className="block text-muted-foreground">{selectedReplacement.split("::")[1]}</span>
														</span>
													)}
												</SelectValue>
											</SelectTrigger>
											<SelectContent>
												{replacements.map((r) => (
													<SelectItem
														key={`${r.path}::${r.function_name}`}
														value={`${r.path}::${r.function_name}`}
													>
														<div className="flex min-w-0 flex-wrap items-center gap-2">
															<FileCode className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
															<span className="min-w-0 basis-full font-mono text-xs leading-5 [overflow-wrap:anywhere]">
																{r.path}
															</span>

															<span className="min-w-0 font-mono text-xs leading-5 [overflow-wrap:anywhere]">
																{
																	r.function_name
																}
															</span>
															<Badge
																variant={
																	r.compatibility ===
																	"exact"
																		? "default"
																		: "secondary"
																}
																className="ml-auto shrink-0"
															>
																{
																	r.compatibility
																}
															</Badge>
														</div>
													</SelectItem>
												))}
											</SelectContent>
										</Select>
										<Button
											className="min-h-11 w-full"
											onClick={handleReplace}
											disabled={
												!selectedReplacement ||
												isActionLoading
											}
										>
											{isActionLoading ? (
												<Loader2
													className={cn(
														"mr-2 h-4 w-4",
														!prefersReducedMotion &&
															"motion-safe:animate-spin",
													)}
												/>
											) : (
												<ArrowRightLeft className="mr-2 h-4 w-4" />
											)}
											Replace
										</Button>
									</>
								) : (
									<div className="rounded-[var(--bf-radius-surface)] border border-dashed border-border/70 bg-muted/30 p-3 text-sm leading-6 text-muted-foreground">
										No compatible replacements found
									</div>
								)}
							</div>

							<div className="space-y-3 rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4 shadow-sm">
								<div className="flex items-center gap-2">
									<RefreshCw className="h-4 w-4 shrink-0 text-muted-foreground" />
									<h4 className="font-medium leading-6">
										Recreate file
									</h4>
								</div>
								<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
									Restore the file at{" "}
									<code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs [overflow-wrap:anywhere]">
										{lastPath}
									</code>{" "}
									with the workflow's saved code.
								</p>
								<Button
									variant="outline"
									className="min-h-11 w-full"
									onClick={handleRecreate}
									disabled={isActionLoading}
								>
									{isActionLoading ? (
										<Loader2
											className={cn(
												"mr-2 h-4 w-4",
												!prefersReducedMotion &&
													"motion-safe:animate-spin",
											)}
										/>
									) : (
										<RefreshCw className="mr-2 h-4 w-4" />
									)}
									Recreate File
								</Button>
							</div>

							<div className="space-y-3 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-4 shadow-sm">
								<div className="flex items-center gap-2">
									<XCircle className="h-4 w-4 shrink-0 text-[var(--bf-danger)]" />
									<h4 className="font-medium leading-6">
										Deactivate
									</h4>
								</div>
								<p className="text-sm leading-6 text-muted-foreground [overflow-wrap:anywhere]">
									Mark this workflow as inactive. Forms and
									apps using it will need to be updated.
								</p>
								{usedBy.length > 0 && (
									<p className="text-xs leading-5 text-[var(--bf-warning)] [overflow-wrap:anywhere]">
										Warning: {usedBy.length}{" "}
										{usedBy.length === 1
											? "entity"
											: "entities"}{" "}
										still{" "}
										{usedBy.length === 1 ? "uses" : "use"}{" "}
										this workflow.
									</p>
								)}
								<Button
									variant="destructive"
									className="min-h-11 w-full"
									onClick={handleDeactivate}
									disabled={isActionLoading}
								>
									{isActionLoading ? (
										<Loader2
											className={cn(
												"mr-2 h-4 w-4",
												!prefersReducedMotion &&
													"motion-safe:animate-spin",
											)}
										/>
									) : (
										<XCircle className="mr-2 h-4 w-4" />
									)}
									Deactivate
								</Button>
							</div>
						</div>
					</div>
					<div className="shrink-0 border-t p-4 sm:px-6">
						<Button
							type="button"
							variant="outline"
							className="min-h-11 w-full sm:w-auto"
							disabled={isActionLoading}
							onClick={onClose}
						>
							Close
						</Button>
					</div>
				</div>
			</DialogContent>
		</Dialog>
	);
}

export default OrphanedWorkflowDialog;
