import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
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

interface PolicyEditorModalProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	location: string;
	scope: string | null;
	path: string;
	onSaved?: () => void;
}

export function PolicyEditorModal(props: PolicyEditorModalProps) {
	if (!props.open) return null;
	return (
		<PolicyEditorSession
			key={JSON.stringify([props.location, props.scope, props.path])}
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
	onSaved,
}: PolicyEditorModalProps) {
	const [showRulesManager, setShowRulesManager] = useState(false);
	const [busy, setBusy] = useState(false);
	const policyQuery = useQuery({
		queryKey: ["file-policy-editor", location, scope, path],
		queryFn: async () => {
			const result = await listFilePolicies({
				location,
				scope: scope ?? undefined,
			});
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
		onOpenChange(false);
	}

	async function handleDelete(policy: FilePolicy) {
		await deleteFilePolicy(policy);
		toast.success("File policy deleted");
		onSaved?.();
		onOpenChange(false);
	}

	return (
		<>
			<Dialog
				open={open}
				onOpenChange={(next) => {
					if (!busy) onOpenChange(next);
				}}
			>
				<DialogContent
					className="flex max-h-[90dvh] flex-col gap-4 overflow-hidden sm:max-w-2xl"
					showCloseButton={!busy}
					onEscapeKeyDown={(event) => {
						if (busy) event.preventDefault();
					}}
					onInteractOutside={(event) => {
						if (busy) event.preventDefault();
					}}
				>
					<DialogHeader>
						<div className="flex flex-wrap items-center justify-between gap-2">
							<DialogTitle>Manage policy</DialogTitle>
							<Button
								type="button"
								size="sm"
								variant="ghost"
								className="min-h-11 text-xs"
								disabled={busy}
								onClick={() => setShowRulesManager(true)}
								data-testid="manage-rules-btn"
							>
								Manage rules…
							</Button>
						</div>
					</DialogHeader>
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
									Retry file policy
								</Button>
							</AlertDescription>
						</Alert>
					)}
					{draft && (
						<FilePolicyEditor
							key={`${draft.id ?? "draft"}:${draft.location}:${draft.organizationId ?? "global"}:${draft.path}`}
							path={path}
							value={draft}
							onSave={handleSave}
							onDelete={handleDelete}
							onBusyChange={setBusy}
						/>
					)}
				</DialogContent>
			</Dialog>

			<Dialog open={showRulesManager} onOpenChange={setShowRulesManager}>
				<DialogContent className="max-h-[90dvh] overflow-auto sm:max-w-2xl">
					<DialogHeader>
						<DialogTitle>File policy rules</DialogTitle>
					</DialogHeader>
					<PolicyRulesManager domain="file" />
				</DialogContent>
			</Dialog>
		</>
	);
}
