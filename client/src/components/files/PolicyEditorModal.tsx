import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ShieldCheck } from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { FilePolicyEditor } from "@/components/files/FilePolicyEditor";
import { PolicyRulesManager } from "@/components/policy-rules/PolicyRulesManager";
import {
	deleteFilePolicy,
	listFilePolicies,
	saveFilePolicy,
	type FilePolicy,
} from "@/services/filePolicies";
import { bestPolicyForPath, makeDefaultPolicy } from "./policyDraft";

export interface PolicyEditorPanelProps {
	location: string;
	scope: string | null;
	path: string;
	exactPath?: string;
	onSaved?: () => void;
	onBusyChange?: (busy: boolean) => void;
	onOpenChange?: (open: boolean) => void;
}

interface PolicyEditorModalProps extends Omit<
	PolicyEditorPanelProps,
	"onOpenChange"
> {
	open: boolean;
	onOpenChange: (open: boolean) => void;
}

type PolicyEditorSessionProps = PolicyEditorPanelProps & {
	open?: boolean;
};

export function PolicyEditorModal(props: PolicyEditorModalProps) {
	if (!props.open) return null;
	return (
		<PolicyEditorSession
			key={JSON.stringify([
				props.location,
				props.scope,
				props.path,
				props.exactPath,
			])}
			{...props}
		/>
	);
}

export function PolicyEditorPanel(props: PolicyEditorPanelProps) {
	return (
		<PolicyEditorSession
			key={JSON.stringify([
				props.location,
				props.scope,
				props.path,
				props.exactPath,
			])}
			{...props}
		/>
	);
}

function PolicyEditorSession({
	open,
	onOpenChange,
	location,
	scope,
	path,
	exactPath,
	onSaved,
	onBusyChange,
}: PolicyEditorSessionProps) {
	const [showRulesManager, setShowRulesManager] = useState(false);
	const [busy, setBusy] = useState(false);
	function handleBusyChange(next: boolean) {
		setBusy(next);
		onBusyChange?.(next);
	}
	const policyQuery = useQuery({
		queryKey: ["file-policy-editor", location, scope, path, exactPath],
		queryFn: async () => {
			const result = await listFilePolicies({
				location,
				scope: scope ?? undefined,
			});
			if (exactPath !== undefined) {
				return (
					(result.policies ?? []).find(
						(policy) =>
							policy.location === location &&
							policy.path === exactPath,
					) ?? {
						...makeDefaultPolicy(path, location, scope),
						path: exactPath,
					}
				);
			}
			return (
				bestPolicyForPath(result.policies ?? [], path, location) ??
				makeDefaultPolicy(path, location, scope)
			);
		},
		retry: false,
		staleTime: Infinity,
		gcTime: 0,
	});
	const draft = policyQuery.data;

	async function handleSave(policy: FilePolicy) {
		await saveFilePolicy(policy);
		toast.success("File policy saved");
		onSaved?.();
		handleBusyChange(false);
		onOpenChange?.(false);
	}

	async function handleDelete(policy: FilePolicy) {
		await deleteFilePolicy(policy);
		toast.success("File policy deleted");
		onSaved?.();
		handleBusyChange(false);
		onOpenChange?.(false);
	}

	const panel = (
		<section className="flex min-h-0 flex-1 flex-col overflow-hidden">
			<div className="shrink-0 space-y-3 border-b border-border/70 p-3">
				<div className="flex items-start gap-3">
					<div className="flex min-w-0 flex-1 items-start gap-3">
						<div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/30">
							<ShieldCheck className="h-4 w-4" />
						</div>
						<div className="min-w-0">
							<h2 className="text-sm font-semibold">
								Manage Policy
							</h2>
						</div>
					</div>
					{onOpenChange && (
						<Button
							type="button"
							size="sm"
							variant="ghost"
							className="min-h-11 shrink-0 text-xs"
							disabled={busy}
							onClick={() => onOpenChange(false)}
						>
							<ArrowLeft className="h-4 w-4" />
							Back to Access
						</Button>
					)}
				</div>
				<p className="text-sm text-muted-foreground">
					Review rules first, then use advanced code for custom
					predicates.
				</p>
				<Button
					type="button"
					size="sm"
					variant="ghost"
					className="min-h-11 w-full justify-start text-xs sm:w-auto"
					disabled={busy}
					onClick={() => setShowRulesManager((next) => !next)}
					data-testid="manage-rules-btn"
				>
					{showRulesManager
						? "Hide Shared Rules"
						: "Advanced Shared Rules…"}
				</Button>
				{draft && (
					<PolicySourceContext
						selectedPath={path}
						policyPath={draft.path}
						exactPath={exactPath}
						location={location}
					/>
				)}
			</div>
			<div className="min-h-0 flex-1 overflow-y-auto p-3">
				<div className="flex min-h-full flex-col gap-4">
					{policyQuery.isPending && (
						<p
							role="status"
							className="py-4 text-sm text-muted-foreground"
						>
							Loading file policy…
						</p>
					)}
					{policyQuery.isError && (
						<Alert variant="destructive">
							<AlertTitle>
								File policy could not be loaded
							</AlertTitle>
							<AlertDescription>
								<p>
									Try again before editing this path’s policy.
								</p>
								<Button
									className="mt-3 min-h-11"
									variant="outline"
									onClick={() => void policyQuery.refetch()}
								>
									Retry File Policy
								</Button>
							</AlertDescription>
						</Alert>
					)}
					{showRulesManager && (
						<section className="shrink-0 rounded-[var(--bf-radius-surface)] border border-border/70 p-3">
							<h3 className="mb-2 text-sm font-medium">
								Advanced Shared Rules
							</h3>
							<p className="mb-3 text-xs text-muted-foreground">
								Shared rule editing keeps its existing
								confirmation dialogs for create, edit, and
								delete operations.
							</p>
							<PolicyRulesManager domain="file" />
						</section>
					)}
					{draft && (
						<FilePolicyEditor
							key={`${draft.id ?? "draft"}:${draft.location}:${draft.organizationId ?? "global"}:${draft.path}`}
							path={path}
							value={draft}
							onSave={handleSave}
							onDelete={handleDelete}
							onBusyChange={handleBusyChange}
							compact
						/>
					)}
				</div>
			</div>
		</section>
	);

	if (open === undefined) return panel;

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!busy) onOpenChange?.(next);
			}}
		>
			<DialogContent
				className="flex max-h-[90dvh] flex-col gap-0 overflow-hidden p-0 sm:max-w-2xl [&_[data-slot=dialog-header]]:pr-16"
				showCloseButton={!busy}
				onEscapeKeyDown={(event) => {
					if (busy) event.preventDefault();
				}}
				onInteractOutside={(event) => {
					if (busy) event.preventDefault();
				}}
			>
				<DialogHeader className="sr-only">
					<DialogTitle>Manage Policy</DialogTitle>
				</DialogHeader>
				{panel}
			</DialogContent>
		</Dialog>
	);
}

function PolicySourceContext({
	selectedPath,
	policyPath,
	exactPath,
	location,
}: {
	selectedPath: string;
	policyPath: string;
	exactPath?: string;
	location: string;
}) {
	const selectedLabel = selectedPath || "Share root";
	const policyLabel = policyPath || "Share root";
	const inherited = exactPath === undefined && policyPath !== selectedPath;
	const exact = exactPath !== undefined;
	const samePath = selectedLabel === policyLabel;
	return (
		<div className="space-y-1 rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 p-3 text-xs">
			<p className="font-medium text-foreground [overflow-wrap:anywhere]">
				{location} / {policyLabel}
			</p>
			<p className="text-muted-foreground [overflow-wrap:anywhere]">
				{exact && samePath
					? `This policy is attached here. Changes affect matching children under ${policyLabel}.`
					: exact
						? `This policy is attached to ${policyLabel}. The selected path is ${selectedLabel}.`
						: inherited
							? `This policy is inherited by ${selectedLabel}. Changes also affect matching children under ${policyLabel}.`
							: `This policy is attached to ${selectedLabel}. Changes affect matching children under this path.`}
			</p>
		</div>
	);
}
