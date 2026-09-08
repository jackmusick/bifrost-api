import { useMemo, useRef, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { Loader2, Plus, RefreshCw } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
} from "@/components/ui/card";
import { SettingsReadError } from "./SettingsReadError";
import { useCreateWorkflowKey, useRevokeWorkflowKey, useWorkflowKeys } from "@/hooks/useWorkflowKeys";
import { useWorkflowsMetadata } from "@/hooks/useWorkflows";
import type { WorkflowKeyResponse } from "@/services/workflowKeys";
import { cn } from "@/lib/utils";
import {
	WorkflowKeyCreateDialog,
	WorkflowKeyRevealDialog,
	WorkflowKeyRevokeDialog,
	type WorkflowKeyFormValues,
} from "./workflow-keys/WorkflowKeyDialogs";
import { WorkflowKeysList } from "./workflow-keys/WorkflowKeysList";

export function WorkflowKeys() {
	const reduceMotion = useReducedMotion() ?? false;
	const spinClassName = reduceMotion
		? ""
		: "animate-spin motion-reduce:animate-none";
	const createButtonRef = useRef<HTMLButtonElement>(null);
	const headingRef = useRef<HTMLHeadingElement>(null);
	const revokeTriggerRef = useRef<HTMLButtonElement | null>(null);
	const createBusyRef = useRef(false);
	const revokeBusyRef = useRef(false);

	const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
	const [isRevealDialogOpen, setIsRevealDialogOpen] = useState(false);
	const [isRevokeDialogOpen, setIsRevokeDialogOpen] = useState(false);
	const [selectedKey, setSelectedKey] = useState<WorkflowKeyResponse | null>(
		null,
	);
	const [createdKey, setCreatedKey] = useState<WorkflowKeyResponse | null>(
		null,
	);
	const [createError, setCreateError] = useState<string | null>(null);
	const [revokeError, setRevokeError] = useState<string | null>(null);
	const [isCreating, setIsCreating] = useState(false);
	const [isRevoking, setIsRevoking] = useState(false);
	const [revokePreferFallback, setRevokePreferFallback] = useState(false);

	const {
		data: keys,
		isLoading: keysLoading,
		isFetching: keysFetching,
		isError: keysError,
		refetch: refetchKeys,
	} = useWorkflowKeys({ includeRevoked: false });

	const {
		data: workflowsData,
		isLoading: workflowsLoading,
		isFetching: workflowsFetching,
		isError: workflowsError,
		hasData: workflowsHasData,
		refetch: refetchWorkflows,
	} = useWorkflowsMetadata();

	const createMutation = useCreateWorkflowKey({ errorToast: false });
	const revokeMutation = useRevokeWorkflowKey({
		errorToast: false,
		successToast: false,
	});

	const workflowList = useMemo(
		() => workflowsData?.workflows ?? [],
		[workflowsData],
	);
	const workflowLookup = useMemo(
		() => {
		const entries: Array<[string, (typeof workflowList)[number]]> = [];
			for (const workflow of workflowList) {
				if (workflow.id) entries.push([workflow.id, workflow]);
			}
			return new Map(entries);
		},
		[workflowList],
	);

	const canResolveOrphans =
		workflowsHasData &&
		!workflowsError &&
		!workflowsLoading &&
		!workflowsFetching;

	const canMutate =
		!keysLoading &&
		!keysFetching &&
		!keysError &&
		!workflowsLoading &&
		!workflowsFetching &&
		!workflowsError;

	const sortedKeys = useMemo(() => {
		if (!keys) return [];

		return [...keys].sort((a, b) => {
			const aGlobal = !a.workflow_id;
			const bGlobal = !b.workflow_id;
			if (aGlobal !== bGlobal) return aGlobal ? -1 : 1;

			if (canResolveOrphans) {
				const aOrphan = Boolean(a.workflow_id && !workflowLookup.has(a.workflow_id));
				const bOrphan = Boolean(b.workflow_id && !workflowLookup.has(b.workflow_id));
				if (aOrphan !== bOrphan) return aOrphan ? 1 : -1;
			}

			return (
				new Date(b.created_at || 0).getTime() -
				new Date(a.created_at || 0).getTime()
			);
		});
	}, [canResolveOrphans, keys, workflowLookup]);

	const availableWorkflowOptions = useMemo(() => {
		if (!keys || !workflowsHasData) return [];

		const keyedWorkflowIds = new Set(
			keys.filter((key) => key.workflow_id).map((key) => key.workflow_id as string),
		);

		return workflowList
			.filter(
				(workflow) =>
					workflow.id &&
					workflow.endpoint_enabled &&
					!workflow.public_endpoint &&
					!keyedWorkflowIds.has(workflow.id),
			)
			.sort((a, b) => (a.name ?? "").localeCompare(b.name ?? ""))
			.map((workflow) => ({
				value: workflow.id as string,
				label: workflow.name ?? workflow.id ?? "Unnamed workflow",
			}));
	}, [keys, workflowList, workflowsHasData]);

	const keysReadError = keysError ? (
		<SettingsReadError
			resource="workflow keys"
			cached={Boolean(keys)}
			pending={keysFetching}
			onRetry={() => {
				void refetchKeys();
			}}
		/>
	) : null;

	const workflowsReadError = workflowsError ? (
		<SettingsReadError
			resource="workflow metadata"
			cached={workflowsHasData}
			pending={workflowsFetching}
			onRetry={() => {
				void refetchWorkflows();
			}}
		/>
	) : null;

	const showInitialLoader = !keys && keysLoading;
	const shouldRenderList = !keysError || Boolean(keys);

	const handleRefresh = () => {
		void refetchKeys();
		void refetchWorkflows();
	};

	const handleCreateOpen = () => {
		if (!canMutate) return;
		setCreateError(null);
		setIsCreateDialogOpen(true);
	};

	const handleCreateSubmit = async (values: WorkflowKeyFormValues) => {
		if (createBusyRef.current || !canMutate) return;

		createBusyRef.current = true;
		setIsCreating(true);
		setCreateError(null);

		try {
			const result = await createMutation.mutateAsync({
				workflow_id: values.isGlobal ? undefined : values.workflowId,
				expires_in_days: values.expiresInDays
					? parseInt(values.expiresInDays)
					: undefined,
				description: values.description,
				disable_global_key: false,
			});

			setCreatedKey(result);
			setIsCreateDialogOpen(false);
			setIsRevealDialogOpen(true);
		} catch (error) {
			setCreateError(
				error instanceof Error
					? error.message
					: "Could not create the API key. Try again.",
			);
		} finally {
			createBusyRef.current = false;
			setIsCreating(false);
		}
	};

	const handleOpenRevoke = (
		key: WorkflowKeyResponse,
		trigger: HTMLButtonElement,
	) => {
		if (!canMutate) return;
		revokeTriggerRef.current = trigger;
		setRevokePreferFallback(false);
		setSelectedKey(key);
		setRevokeError(null);
		setIsRevokeDialogOpen(true);
	};

	const handleConfirmRevoke = async () => {
		if (!selectedKey?.id || revokeBusyRef.current || !canMutate) return;

		revokeBusyRef.current = true;
		setIsRevoking(true);
		setRevokeError(null);

		try {
			await revokeMutation.mutateAsync(selectedKey.id);
			setRevokePreferFallback(true);
			setIsRevokeDialogOpen(false);
			setSelectedKey(null);
		} catch (error) {
			setRevokeError(
				error instanceof Error
					? error.message
					: "Could not revoke the API key. Try again.",
			);
		} finally {
			revokeBusyRef.current = false;
			setIsRevoking(false);
		}
	};

	const currentRevealKey = createdKey;
	const revealScopeLabel = currentRevealKey?.workflow_name
		? currentRevealKey.workflow_name
		: currentRevealKey?.workflow_id || "Global";
	const revealExpiresLabel = currentRevealKey?.expires_at
		? formatDate(currentRevealKey.expires_at)
		: "Never";

	return (
		<div className="flex min-w-0 flex-col">
			<Card className="flex flex-1 flex-col overflow-hidden rounded-[var(--bf-radius-surface)]">
				<CardHeader className="flex-shrink-0 border-b border-border/60 pb-4 sm:pb-5">
					<div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
						<div className="space-y-2">
							<h2
								ref={headingRef}
								tabIndex={-1}
								className="font-display text-xl font-semibold tracking-tight outline-none"
							>
								Workflow Keys
							</h2>
							<CardDescription className="max-w-2xl text-pretty">
								Generate API keys for external systems to
								trigger workflows. Global keys work with all
								workflows, workflow-specific keys are scoped to
								individual workflows.
							</CardDescription>
						</div>
						<div className="flex items-center gap-2 self-start lg:self-auto">
							<Button
								ref={createButtonRef}
								variant="outline"
								size="icon"
								className="h-11 w-11 rounded-[var(--bf-radius-control)] sm:h-10 sm:w-10"
								onClick={handleCreateOpen}
								disabled={!canMutate}
								title="Create API Key"
								aria-label="Create API key"
							>
								<Plus className="h-4 w-4" />
							</Button>
							<Button
								variant="outline"
								size="icon"
								className="h-11 w-11 rounded-[var(--bf-radius-control)] sm:h-10 sm:w-10"
								onClick={handleRefresh}
								disabled={keysFetching || workflowsFetching}
								title="Refresh"
								aria-label="Refresh workflow keys"
							>
								<RefreshCw
									className={cn(
										"h-4 w-4",
										(keysFetching || workflowsFetching) &&
											spinClassName,
									)}
								/>
							</Button>
						</div>
					</div>
				</CardHeader>

			<CardContent className="flex flex-1 flex-col overflow-hidden pt-4">
				{(keysReadError || workflowsReadError) && (
					<div className="space-y-4 pb-4">
						{keysReadError}
						{workflowsReadError}
					</div>
				)}

					{showInitialLoader ? (
						<div className="flex items-center justify-center py-16">
							<Loader2
								className={cn(
									"h-8 w-8 text-muted-foreground",
									spinClassName,
								)}
							/>
						</div>
					) : shouldRenderList ? (
						<WorkflowKeysList
							keys={sortedKeys}
							workflowLookup={workflowLookup}
							canResolveOrphans={canResolveOrphans}
							canMutate={canMutate}
							onCreate={handleCreateOpen}
							onRevoke={handleOpenRevoke}
						/>
					) : null}
				</CardContent>
			</Card>

			<WorkflowKeyCreateDialog
				key={`create-${isCreateDialogOpen ? "open" : "closed"}`}
				open={isCreateDialogOpen}
				onOpenChange={(open) => {
					setIsCreateDialogOpen(open);
					if (!open) setCreateError(null);
				}}
				onSubmit={handleCreateSubmit}
				pending={isCreating}
				error={createError}
				canSubmit={canMutate}
				workflowOptions={availableWorkflowOptions}
				returnFocusRef={createButtonRef}
			/>

			<WorkflowKeyRevealDialog
				key={`reveal-${currentRevealKey?.id ?? "closed"}`}
				open={isRevealDialogOpen}
				onOpenChange={(open) => {
					setIsRevealDialogOpen(open);
					if (!open) setCreatedKey(null);
				}}
				rawKey={currentRevealKey?.raw_key || ""}
				description={currentRevealKey?.description}
					scopeLabel={revealScopeLabel}
					workflowId={currentRevealKey?.workflow_id}
					expiresLabel={revealExpiresLabel}
					returnFocusRef={createButtonRef}
				/>

			<WorkflowKeyRevokeDialog
				open={isRevokeDialogOpen}
				onOpenChange={(open) => {
					setIsRevokeDialogOpen(open);
					if (!open) {
						setSelectedKey(null);
						setRevokeError(null);
					}
				}}
					keyLabel={selectedKey?.masked_key || ""}
					error={revokeError}
					pending={isRevoking}
					onConfirm={handleConfirmRevoke}
					returnFocusRef={revokeTriggerRef}
					preferFallback={revokePreferFallback}
					fallbackRef={headingRef}
				/>
			</div>
		);
	}

function formatDate(dateString?: string | null) {
	if (!dateString) return "Never";
	const date = new Date(dateString);
	return date.toLocaleDateString("en-US", {
		month: "short",
		day: "numeric",
		year: "numeric",
		hour: "2-digit",
		minute: "2-digit",
	});
}
