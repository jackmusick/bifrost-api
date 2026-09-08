/**
 * PolicyRulesManager — inline CRUD manager for named policy rules.
 *
 * Lists all rules for a given domain; lets admins create, edit, and delete
 * them. Built-in rules (is_builtin=true) render read-only with a badge.
 *
 * DELETE path surfaces the 409+usages blast-radius before the rule is gone.
 * SAVE path pre-fetches usages when editing so the user sees impact before
 * committing a change.
 */

import { useEffect, useRef, useState } from "react";
import { Plus, Loader2, Lock } from "lucide-react";
import { toast } from "sonner";

import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogFooter,
} from "@/components/ui/dialog";
import {
	AlertDialog,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
	Table,
	TableBody,
	TableCell,
	TableHead,
	TableHeader,
	TableRow,
} from "@/components/ui/table";
import { PolicyRuleActions } from "./PolicyRuleActions";
import { PolicyRuleSurface } from "./PolicyRuleSurface";

import {
	listPolicyRules,
	createPolicyRule,
	updatePolicyRule,
	deletePolicyRule,
	policyRuleUsages,
	type PolicyRule,
	type PolicyRuleInUseError,
} from "@/services/policyRules";

export interface PolicyRulesManagerProps {
	domain: "file" | "table";
}

interface RuleFormState {
	name: string;
	description: string;
	/** Serialised JSON body */
	bodyJson: string;
}

const EMPTY_FORM: RuleFormState = {
	name: "",
	description: "",
	bodyJson: '{\n  "actions": ["read"],\n  "when": null\n}',
};

function isInUseError(
	err: unknown,
): err is Error & { cause: PolicyRuleInUseError } {
	return (
		err instanceof Error &&
		typeof (err as Error & { cause?: unknown }).cause === "object" &&
		(err as Error & { cause?: unknown }).cause !== null &&
		(
			(err as Error & { cause?: { type?: unknown } }).cause as {
				type?: unknown;
			}
		).type === "in_use"
	);
}

export function PolicyRulesManager({ domain }: PolicyRulesManagerProps) {
	const createRef = useRef<HTMLButtonElement>(null);
	const formFocus = useDialogReturnFocus(createRef, true);
	const deleteFocus = useDialogReturnFocus(createRef, true);
	const inUseFocus = useDialogReturnFocus(createRef, true);
	const usageRevision = useRef(0);
	const saveBusy = useRef(false);
	const deleteBusy = useRef(false);
	const [deleteError, setDeleteError] = useState<string | null>(null);
	const deleteErrorRef = useRef<HTMLParagraphElement>(null);
	const formErrorRef = useRef<HTMLParagraphElement>(null);
	const [rules, setRules] = useState<PolicyRule[]>([]);
	const [loading, setLoading] = useState(true);
	const [loadError, setLoadError] = useState<string | null>(null);

	// Form dialog: null = closed, { mode:"create" } = creating, { mode:"edit", rule } = editing
	const [formTarget, setFormTarget] = useState<
		{ mode: "create" } | { mode: "edit"; rule: PolicyRule } | null
	>(null);
	const [form, setForm] = useState<RuleFormState>(EMPTY_FORM);
	const [formError, setFormError] = useState<string | null>(null);
	const [saving, setSaving] = useState(false);

	// Delete confirmation
	const [deleteTarget, setDeleteTarget] = useState<PolicyRule | null>(null);
	const [deleting, setDeleting] = useState(false);

	// Blast-radius state: populated when DELETE returns 409
	const [blastRadius, setBlastRadius] = useState<PolicyRuleInUseError | null>(
		null,
	);

	// Edit usages: informational — shows impact before saving, does NOT block editing
	const [editUsages, setEditUsages] = useState<{
		file_policies: PolicyRuleInUseError["usages"]["file_policies"];
		tables: PolicyRuleInUseError["usages"]["tables"];
		total: number;
	} | null>(null);

	useEffect(() => {
		if (formError) {
			formErrorRef.current?.focus();
			formErrorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [formError]);

	useEffect(() => {
		if (deleteError) {
			deleteErrorRef.current?.focus();
			deleteErrorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [deleteError]);

	async function reload() {
		setLoading(true);
		setLoadError(null);
		try {
			const data = await listPolicyRules(domain);
			setRules(data);
		} catch {
			setLoadError("Failed to load policy rules");
			toast.error("Failed to load policy rules");
		} finally {
			setLoading(false);
		}
	}

	useEffect(() => {
		// Call reload in a nested async fn so setState calls remain inside a
		// callback and satisfy react-hooks/set-state-in-effect.
		const run = async () => {
			await reload();
		};
		void run();
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, [domain]);

	function openCreate() {
		usageRevision.current++;
		setEditUsages(null);
		setForm(EMPTY_FORM);
		setFormError(null);
		setFormTarget({ mode: "create" });
	}

	function openEdit(rule: PolicyRule) {
		usageRevision.current++;
		setForm({
			name: rule.name,
			description: rule.description ?? "",
			bodyJson: JSON.stringify(rule.body, null, 2),
		});
		setFormError(null);
		setEditUsages(null);
		setFormTarget({ mode: "edit", rule });
	}

	function closeForm() {
		if (saveBusy.current) return;
		usageRevision.current++;
		setFormTarget(null);
		setFormError(null);
		setEditUsages(null);
	}

	async function handleSave() {
		if (saveBusy.current || !formTarget) return;
		setFormError(null);
		let parsed: Record<string, unknown>;
		try {
			parsed = JSON.parse(form.bodyJson) as Record<string, unknown>;
		} catch {
			setFormError("Body must be valid JSON.");
			return;
		}

		if (
			parsed === null ||
			Array.isArray(parsed) ||
			typeof parsed !== "object"
		) {
			setFormError("Body must be a JSON object.");
			return;
		}
		saveBusy.current = true;
		setSaving(true);
		try {
			if (formTarget?.mode === "create") {
				await createPolicyRule({
					name: form.name.trim(),
					domain,
					description: form.description.trim() || null,
					body: parsed,
				});
				toast.success("Policy rule created");
			} else if (formTarget?.mode === "edit") {
				const rule = formTarget.rule;
				await updatePolicyRule(rule.domain, rule.name, {
					name:
						form.name.trim() !== rule.name
							? form.name.trim()
							: undefined,
					description: form.description.trim() || null,
					body: parsed,
				});
				toast.success("Policy rule updated");
			}
			saveBusy.current = false;
			closeForm();
			void reload();
		} catch (err) {
			setFormError(err instanceof Error ? err.message : "Save failed");
		} finally {
			saveBusy.current = false;
			setSaving(false);
		}
	}

	function openDelete(rule: PolicyRule) {
		setDeleteError(null);
		setDeleteTarget(rule);
		setBlastRadius(null);
	}

	async function handleDelete() {
		if (!deleteTarget || deleteBusy.current) return;
		deleteBusy.current = true;
		setDeleteError(null);
		setDeleting(true);
		try {
			await deletePolicyRule(deleteTarget.domain, deleteTarget.name);
			toast.success("Policy rule deleted");
			setDeleteTarget(null);
			void reload();
		} catch (err) {
			if (isInUseError(err)) {
				setBlastRadius(err.cause);
			} else {
				setDeleteError(
					err instanceof Error
						? err.message
						: "Failed to delete policy rule",
				);
			}
		} finally {
			deleteBusy.current = false;
			setDeleting(false);
		}
	}

	async function handlePreviewUsages(rule: PolicyRule) {
		const revision = usageRevision.current;
		try {
			const usages = await policyRuleUsages(rule.domain, rule.name);
			if (revision === usageRevision.current && usages.total > 0) {
				// Informational only — editing a referenced rule IS allowed.
				// Store usages separately so the edit dialog can show an impact banner
				// without triggering the delete/blast-radius AlertDialog.
				setEditUsages(usages);
			}
		} catch {
			// Best-effort — if usages fetch fails, just proceed with the edit.
		}
	}

	const domainLabel = domain === "file" ? "file" : "table";

	return (
		<div
			className="@container space-y-3"
			data-testid="policy-rules-manager"
		>
			<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
				<p className="text-sm text-muted-foreground">
					Reusable named rules for {domainLabel} policies
				</p>
				<Button
					type="button"
					size="sm"
					variant="outline"
					onClick={openCreate}
					ref={createRef}
					data-testid="policy-rules-create-btn"
					className="min-h-11"
				>
					<Plus className="h-4 w-4 mr-1" />
					New rule
				</Button>
			</div>

			{loading ? (
				<div className="flex min-h-24 items-center justify-center rounded-[var(--bf-radius-surface)] border border-border/70 bg-card p-4 text-sm text-muted-foreground">
					<div className="flex items-center gap-2">
						<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
						Loading rules…
					</div>
				</div>
			) : loadError ? (
				<div
					role="alert"
					className="flex flex-col gap-3 rounded-[var(--bf-radius-surface)] border border-[var(--bf-danger)]/20 bg-[var(--bf-danger-soft)]/60 p-4 sm:flex-row sm:items-center sm:justify-between"
				>
					<div className="space-y-1">
						<p className="text-sm font-medium text-[var(--bf-danger)]">
							{loadError}
						</p>
						<p className="text-xs text-muted-foreground">
							Retry to reload the rule list.
						</p>
					</div>
					<Button
						type="button"
						variant="outline"
						onClick={() => void reload()}
						className="min-h-11"
					>
						Retry
					</Button>
				</div>
			) : rules.length === 0 ? (
				<div className="rounded-[var(--bf-radius-surface)] border border-dashed border-border/70 bg-card p-6 text-center text-sm text-muted-foreground">
					No {domainLabel} policy rules yet.
				</div>
			) : (
				<div className="space-y-4">
					<div className="space-y-3 @min-[40rem]:hidden">
						{rules.map((rule) => (
							<PolicyRuleSurface
								key={rule.id}
								rule={rule}
								onEdit={() => {
									openEdit(rule);
									void handlePreviewUsages(rule);
								}}
								onDelete={() => openDelete(rule)}
							/>
						))}
					</div>

					<div className="hidden overflow-x-auto rounded-[var(--bf-radius-surface)] border border-border/70 bg-card @min-[40rem]:block">
						<Table className="min-w-[640px]">
							<TableHeader>
								<TableRow>
									<TableHead>Name</TableHead>
									<TableHead>Description</TableHead>
									<TableHead className="w-32" />
								</TableRow>
							</TableHeader>
							<TableBody>
								{rules.map((rule) => (
									<TableRow
										key={rule.id}
										data-testid="policy-rule-row"
									>
										<TableCell className="font-mono text-sm">
											<div className="flex items-center gap-2">
												{rule.name}
												{rule.is_builtin && (
													<Badge
														variant="secondary"
														className="gap-1 text-xs"
														data-testid="builtin-badge"
													>
														<Lock className="h-3 w-3" />
														built-in
													</Badge>
												)}
											</div>
										</TableCell>
										<TableCell className="text-sm text-muted-foreground">
											{rule.description ?? "—"}
										</TableCell>
										<TableCell>
											<PolicyRuleActions
												rule={rule}
												onEdit={() => {
													openEdit(rule);
													void handlePreviewUsages(
														rule,
													);
												}}
												onDelete={() =>
													openDelete(rule)
												}
											/>
										</TableCell>
									</TableRow>
								))}
							</TableBody>
						</Table>
					</div>
				</div>
			)}

			{/* Create / Edit dialog */}
			<Dialog
				open={formTarget !== null}
				onOpenChange={(open) => {
					if (!open) closeForm();
				}}
			>
				<DialogContent
					{...formFocus}
					className="w-[calc(100vw-1rem)] max-h-[92dvh] overflow-y-auto sm:max-w-lg"
				>
					<DialogHeader>
						<DialogTitle>
							{formTarget?.mode === "create"
								? "Create policy rule"
								: `Edit "${formTarget?.mode === "edit" ? formTarget.rule.name : ""}"`}
						</DialogTitle>
					</DialogHeader>

					<div className="space-y-4 py-2">
						<div className="space-y-1.5">
							<Label htmlFor="rule-name">Name</Label>
							<Input
								id="rule-name"
								value={form.name}
								onChange={(e) =>
									setForm((f) => ({
										...f,
										name: e.target.value,
									}))
								}
								placeholder="e.g. admin_access"
								disabled={
									saving || formTarget?.mode !== "create"
								}
							/>
							{formTarget?.mode !== "create" && (
								<p className="text-xs text-muted-foreground">
									Rule names cannot be changed after creation.
								</p>
							)}
						</div>

						<div className="space-y-1.5">
							<Label htmlFor="rule-description">
								Description
							</Label>
							<Input
								id="rule-description"
								disabled={saving}
								value={form.description}
								onChange={(e) =>
									setForm((f) => ({
										...f,
										description: e.target.value,
									}))
								}
								placeholder="Short description (optional)"
							/>
						</div>

						<div className="space-y-1.5">
							<Label htmlFor="rule-body">Body (JSON)</Label>
							<Textarea
								id="rule-body"
								disabled={saving}
								value={form.bodyJson}
								onChange={(e) =>
									setForm((f) => ({
										...f,
										bodyJson: e.target.value,
									}))
								}
								className="font-mono text-xs min-h-[160px]"
								data-testid="rule-body-textarea"
							/>
						</div>

						{formTarget?.mode === "edit" &&
							editUsages &&
							editUsages.total > 0 && (
								<div
									className="rounded-[var(--bf-radius-control)] border border-[var(--bf-info)]/20 bg-[var(--bf-info-soft)]/60 px-3 py-2 text-sm text-[var(--bf-info)]"
									role="status"
									data-testid="edit-usages-banner"
								>
									This rule is referenced by{" "}
									{editUsages.file_policies.length > 0 && (
										<span>
											{editUsages.file_policies.length}{" "}
											file{" "}
											{editUsages.file_policies.length ===
											1
												? "policy"
												: "policies"}
										</span>
									)}
									{editUsages.file_policies.length > 0 &&
										editUsages.tables.length > 0 &&
										" and "}
									{editUsages.tables.length > 0 && (
										<span>
											{editUsages.tables.length}{" "}
											{editUsages.tables.length === 1
												? "table"
												: "tables"}
										</span>
									)}
									. Saving changes will apply everywhere
									it&apos;s used.
								</div>
							)}

						{formError && (
							<p
								className="scroll-mb-24 text-sm text-destructive outline-none"
								role="alert"
								ref={formErrorRef}
								tabIndex={-1}
								data-testid="form-error"
							>
								{formError}
							</p>
						)}
					</div>

					<DialogFooter>
						<Button
							variant="outline"
							onClick={closeForm}
							disabled={saving}
							className="min-h-11"
						>
							Cancel
						</Button>
						<Button
							onClick={handleSave}
							disabled={saving || !form.name.trim()}
							className="min-h-11"
						>
							{saving && (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							)}
							{formTarget?.mode === "create" ? "Create" : "Save"}
						</Button>
					</DialogFooter>
				</DialogContent>
			</Dialog>

			{/* Delete confirmation — plain when rule has no usages */}
			<AlertDialog
				open={deleteTarget !== null && blastRadius === null}
				onOpenChange={(open) => {
					if (!open && !deleteBusy.current) setDeleteTarget(null);
				}}
			>
				<AlertDialogContent
					{...deleteFocus}
					className="max-h-[90dvh] overflow-y-auto"
					onEscapeKeyDown={(event) => {
						if (deleteBusy.current) event.preventDefault();
					}}
				>
					<AlertDialogHeader>
						<AlertDialogTitle>Delete policy rule?</AlertDialogTitle>
						<AlertDialogDescription>
							<span>
								Delete{" "}
								<span className="font-mono">
									{deleteTarget?.name}
								</span>
								? This cannot be undone.
							</span>
						</AlertDialogDescription>
					</AlertDialogHeader>
					{deleteError && (
						<p
							ref={deleteErrorRef}
							tabIndex={-1}
							role="alert"
							className="text-sm text-destructive outline-none [overflow-wrap:anywhere]"
						>
							{deleteError}
						</p>
					)}
					<AlertDialogFooter>
						<AlertDialogCancel disabled={deleting}>
							Cancel
						</AlertDialogCancel>
						<Button
							variant="destructive"
							onClick={handleDelete}
							disabled={deleting}
							className="min-h-11"
						>
							{deleting ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : null}
							Delete
						</Button>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>

			{/* Blast-radius dialog: shown when DELETE returns 409 (delete-flow only) */}
			<AlertDialog
				open={blastRadius !== null}
				onOpenChange={(open) => {
					if (!open) {
						setBlastRadius(null);
						setDeleteTarget(null);
					}
				}}
			>
				<AlertDialogContent
					{...inUseFocus}
					className="max-h-[90dvh] overflow-y-auto [overflow-wrap:anywhere]"
					data-testid="blast-radius-dialog"
				>
					<AlertDialogHeader>
						<AlertDialogTitle>Rule is in use</AlertDialogTitle>
						<AlertDialogDescription asChild>
							<div className="space-y-3">
								<p>{blastRadius?.message}</p>
								{blastRadius &&
									blastRadius.usages.file_policies.length >
										0 && (
										<div>
											<p className="font-medium text-sm mb-1">
												File policies (
												{
													blastRadius.usages
														.file_policies.length
												}
												)
											</p>
											<ul className="text-xs space-y-0.5 list-disc list-inside">
												{blastRadius.usages.file_policies.map(
													(fp) => (
														<li
															key={fp.id}
															data-testid="blast-file-policy"
														>
															{fp.location}/
															{fp.path}
														</li>
													),
												)}
											</ul>
										</div>
									)}
								{blastRadius &&
									blastRadius.usages.tables.length > 0 && (
										<div>
											<p className="font-medium text-sm mb-1">
												Tables (
												{
													blastRadius.usages.tables
														.length
												}
												)
											</p>
											<ul className="text-xs space-y-0.5 list-disc list-inside">
												{blastRadius.usages.tables.map(
													(tb) => (
														<li
															key={tb.id}
															data-testid="blast-table"
														>
															{tb.name}
														</li>
													),
												)}
											</ul>
										</div>
									)}
								<p className="text-sm text-destructive font-medium">
									Deleting this rule will affect all of the
									above. You must remove all references first.
								</p>
							</div>
						</AlertDialogDescription>
					</AlertDialogHeader>
					<AlertDialogFooter>
						<AlertDialogCancel>Close</AlertDialogCancel>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
