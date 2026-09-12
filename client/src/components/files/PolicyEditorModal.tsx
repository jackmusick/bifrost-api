import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
	ArrowLeft,
	ShieldCheck,
	Library,
	X,
	LockKeyhole,
	ArrowUpRight,
} from "lucide-react";
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { toast } from "sonner";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { PolicySummary } from "./EffectiveAccessPanel";
import { listPolicyRules } from "@/services/policyRules";
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
	onOpenSource?: (policy: FilePolicy) => void;
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
	onOpenSource,
	onBusyChange,
}: PolicyEditorSessionProps) {
	const [showRulesManager, setShowRulesManager] = useState(false);
	const [busy, setBusy] = useState(false);
	function handleBusyChange(next: boolean) {
		setBusy(next);
		onBusyChange?.(next);
	}
	const policyQuery = useQuery({
		queryKey: [
			"file-policy-editor",
			location,
			scope,
			path,
			exactPath,
			open === undefined,
		],
		queryFn: async () => {
			const result = await listFilePolicies({
				location,
				scope: scope ?? undefined,
			});
			const policies = result.policies ?? [];
			const target = exactPath ?? path;
			const attached = policies.find(
				(policy) =>
					policy.location === location && policy.path === target,
			);
			const inherited = bestPolicyForPath(
				policies.filter((policy) => policy.path !== target),
				target,
				location,
			);
			const draft =
				exactPath !== undefined || open === undefined
					? (attached ?? {
							...makeDefaultPolicy(target, location, scope),
							path: target,
						})
					: (bestPolicyForPath(policies, path, location) ??
						makeDefaultPolicy(path, location, scope));
			return {
				draft,
				inherited:
					!attached && inherited?.path !== draft.path
						? inherited
						: null,
			};
		},
		retry: false,
		staleTime: Infinity,
		gcTime: 0,
	});
	const draft = policyQuery.data?.draft;
	const inherited = policyQuery.data?.inherited;
	const ruleQuery = useQuery({
		queryKey: ["policy-rules", "file"],
		queryFn: () => listPolicyRules("file"),
		enabled: Boolean(inherited),
		retry: false,
	});
	const namedRules = new Map(
		(ruleQuery.data ?? []).map((rule) => [rule.name, rule]),
	);

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
				{onOpenChange && (
					<Button
						type="button"
						variant="ghost"
						size="sm"
						className="-ml-2 min-h-11 justify-start px-2 text-xs text-muted-foreground"
						disabled={busy}
						onClick={() => onOpenChange(false)}
					>
						<ArrowLeft className="size-4" />
						Back to Access
					</Button>
				)}
				<div className="flex min-h-6 items-center gap-2">
					<ShieldCheck className="size-4 shrink-0 text-primary" />
					<h2 className="text-sm font-semibold">Manage Policy</h2>
				</div>
				<p className="text-xs leading-5 text-muted-foreground">
					Choose the rules that grant access to these files.
				</p>
				{draft && (
					<PolicySourceContext
						selectedPath={path}
						policyPath={draft.path}
						exists={Boolean(draft.id)}
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
					{inherited && (
						<section
							aria-label="Inherited Access"
							className="rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 p-3 text-sm"
						>
							<div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
								<LockKeyhole className="size-4" />
								<h3>Inherited Access</h3>
								<span className="ml-auto">Read-Only</span>
							</div>
							{onOpenSource ? (
								<Button
									type="button"
									variant="link"
									className="h-auto min-h-11 max-w-full justify-start whitespace-normal px-0 text-left"
									disabled={busy}
									onClick={() => onOpenSource(inherited)}
								>
									{inherited.location} /{" "}
									{inherited.path || "Share root"}
									<ArrowUpRight className="size-4 shrink-0" />
								</Button>
							) : (
								<p className="mt-2 text-xs text-muted-foreground">
									{inherited.location} /{" "}
									{inherited.path || "Share root"}
								</p>
							)}
							<PolicySummary
								policy={inherited}
								namedRules={namedRules}
								rulesLoading={ruleQuery.isFetching}
							/>
						</section>
					)}
					<section
						aria-label="Shared Rule Library"
						className="shrink-0 rounded-[var(--bf-radius-surface)] border border-[var(--bf-info)]/30 bg-[var(--bf-info-soft)] p-3"
					>
						<div className="flex items-center gap-2">
							<Library className="size-4 shrink-0 text-[var(--bf-info)]" />
							<h3 className="min-w-0 flex-1 text-sm font-medium text-[var(--bf-info)]">
								Shared Rule Library
							</h3>
							{showRulesManager ? (
								<Button
									type="button"
									size="icon"
									variant="ghost"
									aria-label="Close Shared Rule Library"
									disabled={busy}
									onClick={() => setShowRulesManager(false)}
								>
									<X className="size-4" />
								</Button>
							) : (
								<Button
									type="button"
									size="sm"
									variant="outline"
									className="min-h-11"
									disabled={busy}
									onClick={() => setShowRulesManager(true)}
									data-testid="manage-rules-btn"
								>
									Open Library
								</Button>
							)}
						</div>
						<p className="mt-2 text-xs leading-5 text-muted-foreground">
							Reusable rules shared across policies. Create or
							edit a rule here, then add it to this policy below.
						</p>
						{showRulesManager && (
							<div className="mt-3 border-t border-[var(--bf-info)]/30 pt-3">
								<p className="mb-3 text-xs text-muted-foreground">
									Editing a shared rule updates every policy
									that uses it.
								</p>
								<PolicyRulesManager domain="file" />
							</div>
						)}
					</section>
					{draft && (
						<div className="space-y-1">
							<h3 className="text-sm font-semibold">
								Rules on This Path
							</h3>
							{inherited && (
								<p className="text-xs leading-5 text-muted-foreground">
									Saving rules here replaces the inherited
									policy for this path. It does not change the
									source policy.
								</p>
							)}
						</div>
					)}

					{draft && (
						<FilePolicyEditor
							key={`${draft.id ?? "draft"}:${draft.location}:${draft.organizationId ?? "global"}:${draft.path}`}
							path={path}
							value={draft}
							onSave={handleSave}
							onDelete={handleDelete}
							onBusyChange={handleBusyChange}
							rulesRefreshKey={String(showRulesManager)}
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
	policyPath,
	location,
	exists,
}: {
	selectedPath: string;
	policyPath: string;
	location: string;
	exists: boolean;
}) {
	return (
		<div className="space-y-1 text-xs">
			<p className="font-medium text-foreground [overflow-wrap:anywhere]">
				{location} / {policyPath || "Share root"}
			</p>
			<p className="text-muted-foreground">
				{exists
					? "Editing the policy attached to this path."
					: "No policy is set on this path yet."}
			</p>
		</div>
	);
}
