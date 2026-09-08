import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Save, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { JsonYamlEditor } from "@/components/shared/JsonYamlEditor";
import type { FilePolicy, FilePolicies } from "@/services/filePolicies";
import {
	FILE_POLICY_TEMPLATES,
	instantiateFileTemplate,
	type FilePolicyTemplateKey,
} from "./file-policy-templates";
import { FilePolicyReferencePanel } from "./FilePolicyReferencePanel";
import { listPolicyRules, type PolicyRule } from "@/services/policyRules";

interface FilePolicyEditorProps {
	path: string;
	value: FilePolicy;
	onSave: (policy: FilePolicy) => void | Promise<void>;
	onDelete: (policy: FilePolicy) => void | Promise<void>;
	onBusyChange?: (busy: boolean) => void;
}

const POLICY_SEED: FilePolicies = { policies: [] };

/** Only `{policies: [...]}` is accepted as the document root. */
function asFilePolicies(parsed: unknown): FilePolicies {
	if (
		parsed === null ||
		typeof parsed !== "object" ||
		Array.isArray(parsed)
	) {
		throw new Error(
			"Document root must be an object with a `policies` key.",
		);
	}
	if (!Array.isArray((parsed as Record<string, unknown>).policies)) {
		throw new Error("`policies` must be an array.");
	}
	return parsed as FilePolicies;
}

interface SaveError {
	path: string;
	message: string;
}

/** Parse the structured 422 detail from a save attempt. */
function extractSaveErrors(err: unknown): SaveError[] | null {
	if (!(err instanceof Error)) return null;
	// parseResponse() in filePolicies.ts serializes the detail object via
	// JSON.stringify when it isn't a plain string. Try to parse it back.
	try {
		const parsed = JSON.parse(err.message) as { errors?: SaveError[] };
		if (Array.isArray(parsed?.errors)) return parsed.errors;
	} catch {
		// Not JSON — fall through to return null.
	}
	return null;
}

export function FilePolicyEditor({
	path,
	value,
	onSave,
	onDelete,
	onBusyChange,
}: FilePolicyEditorProps) {
	// The editor mutates only the inner policy document; the location/path/org
	// wrapper is fixed by the selection and reattached on save.
	const mutationBusy = useRef(false);
	const errorRef = useRef<HTMLDivElement>(null);
	const [doc, setDoc] = useState<FilePolicies | null>(value.policies ?? null);
	const [parseError, setParseError] = useState<string | null>(null);
	const [templateKey, setTemplateKey] = useState<string>("");
	const [refKey, setRefKey] = useState<string>("");
	const [saving, setSaving] = useState(false);
	const [deleting, setDeleting] = useState(false);
	const [saveErrors, setSaveErrors] = useState<SaveError[] | null>(null);
	const [mutationError, setMutationError] = useState<string | null>(null);
	const [retryAction, setRetryAction] = useState<"save" | "delete" | null>(
		null,
	);
	const [rules, setRules] = useState<PolicyRule[]>([]);
	const [rulesError, setRulesError] = useState<string | null>(null);

	useEffect(() => {
		if (saveErrors || mutationError) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [saveErrors, mutationError]);

	const loadRules = useCallback(async () => {
		setRulesError(null);
		try {
			const next = await listPolicyRules("file");
			setRules(next);
		} catch {
			setRules([]);
			setRulesError("Unable to load file policy rules.");
		}
	}, []);

	useEffect(() => {
		void (async () => {
			await loadRules();
		})();
	}, [loadRules]);

	useEffect(() => {
		onBusyChange?.(saving || deleting);
	}, [deleting, onBusyChange, saving]);

	const paths = useMemo(
		() => ({ json: "file-policies.json", yaml: "file-policies.yaml" }),
		[],
	);

	function handleTemplate(key: string) {
		if (!key) return;
		const tpl = instantiateFileTemplate(key as FilePolicyTemplateKey);
		const current = doc?.policies ?? [];
		setDoc({ policies: [...current, tpl] });
		setTemplateKey("");
	}

	function handleRef(name: string) {
		if (!name) return;
		const current = doc?.policies ?? [];
		setDoc({ policies: [...current, { $ref: name }] });
		setRefKey("");
	}

	async function handleSave() {
		if (mutationBusy.current || mutationsDisabled) return;
		mutationBusy.current = true;
		setRetryAction(null);
		setSaving(true);
		setSaveErrors(null);
		setMutationError(null);
		try {
			await onSave({ ...value, policies: doc ?? { policies: [] } });
		} catch (err) {
			const structured = extractSaveErrors(err);
			if (structured) {
				setSaveErrors(structured);
				setRetryAction("save");
			} else {
				setMutationError(
					err instanceof Error ? err.message : String(err),
				);
				setRetryAction("save");
			}
		} finally {
			mutationBusy.current = false;
			setSaving(false);
		}
	}

	async function handleDelete() {
		if (mutationBusy.current || mutationsDisabled || !value.id) return;
		mutationBusy.current = true;
		setRetryAction(null);
		setDeleting(true);
		setSaveErrors(null);
		setMutationError(null);
		try {
			await onDelete(value);
		} catch (err) {
			setMutationError(err instanceof Error ? err.message : String(err));
			setRetryAction("delete");
		} finally {
			mutationBusy.current = false;
			setDeleting(false);
		}
	}

	function handleRetry() {
		if (mutationsDisabled) return;
		if (retryAction === "delete") {
			void handleDelete();
			return;
		}
		void handleSave();
	}

	const mutationsDisabled = parseError !== null || saving || deleting;
	const busy = saving || deleting;
	const effectivePath = path || value.path;

	return (
		<section className="flex min-h-0 flex-1 flex-col gap-3">
			<div className="min-h-0 flex-1 space-y-3 overflow-y-auto pr-1">
				<div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-3">
					<div className="space-y-1">
						<p className="break-words text-xs font-medium text-foreground">
							{value.location}
						</p>
						<p className="break-words text-xs text-muted-foreground">
							{effectivePath ? `/${effectivePath}` : "/(root)"}
						</p>
					</div>
				</div>

				<div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
					<Select
						value={templateKey}
						onValueChange={handleTemplate}
						disabled={mutationsDisabled}
					>
						<SelectTrigger
							className="h-11 w-full min-w-0 sm:w-[200px]"
							aria-label="Insert template"
						>
							<SelectValue placeholder="Insert template…" />
						</SelectTrigger>
						<SelectContent>
							{Object.keys(FILE_POLICY_TEMPLATES).map((k) => (
								<SelectItem key={k} value={k}>
									{k}
								</SelectItem>
							))}
						</SelectContent>
					</Select>
					{rules.length > 0 && (
						<Select
							value={refKey}
							onValueChange={handleRef}
							disabled={mutationsDisabled}
						>
							<SelectTrigger
								className="h-11 w-full min-w-0 sm:w-[200px]"
								aria-label="Insert reference"
							>
								<SelectValue placeholder="Insert reference…" />
							</SelectTrigger>
							<SelectContent>
								{rules.map((r) => (
									<SelectItem key={r.name} value={r.name}>
										{r.name}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					)}
					<div className="shrink-0 sm:ml-auto">
						<FilePolicyReferencePanel />
					</div>
				</div>

				<JsonYamlEditor<FilePolicies>
					value={doc}
					onChange={(next) => {
						setDoc(next);
						setSaveErrors(null);
						setMutationError(null);
						setRetryAction(null);
					}}
					schema={{}}
					seed={POLICY_SEED}
					defaultFormat="yaml"
					paths={paths}
					validateParsed={asFilePolicies}
					onParseErrorChange={setParseError}
					hideParseError
				/>

				{rulesError && (
					<div className="rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/30 p-3 text-xs text-muted-foreground">
						<p className="font-medium text-foreground">
							{rulesError}
						</p>
						<Button
							type="button"
							variant="ghost"
							size="sm"
							className="mt-2 h-11 px-3"
							onClick={() => {
								void loadRules();
							}}
						>
							Retry loading rules
						</Button>
					</div>
				)}
			</div>

			{parseError && (
				<p className="shrink-0 text-xs text-destructive" role="alert">
					Parse error: {parseError}
				</p>
			)}

			{!parseError && (saveErrors || mutationError) && (
				<div
					ref={errorRef}
					tabIndex={-1}
					className="outline-none max-h-32 shrink-0 space-y-1 overflow-y-auto rounded-[var(--bf-radius-surface)] border border-border/70 bg-muted/20 p-3 text-xs text-destructive [overflow-wrap:anywhere]"
					role="alert"
					data-testid="file-policy-save-errors"
				>
					{saveErrors && saveErrors.length > 0 && (
						<>
							<p className="font-medium">Save errors:</p>
							{saveErrors.map((err, i) => (
								<p
									key={`${err.path}:${err.message}:${i}`}
									data-testid="file-policy-save-error"
								>
									{err.path}: {err.message}
								</p>
							))}
						</>
					)}
					{mutationError && (
						<>
							<p className="font-medium">
								{retryAction === "delete"
									? "Delete failed:"
									: "Save failed:"}
							</p>
							<p>{mutationError}</p>
						</>
					)}
					<Button
						type="button"
						variant="ghost"
						size="sm"
						className="h-11 px-3"
						onClick={handleRetry}
					>
						Retry {retryAction === "delete" ? "delete" : "save"}
					</Button>
				</div>
			)}

			<div className="flex items-center justify-end gap-2 border-t border-border/60 pt-3">
				<Button
					type="button"
					variant="outline"
					size="sm"
					className="h-11"
					onClick={handleDelete}
					disabled={!value.id || busy || parseError !== null}
				>
					<Trash2 className="h-4 w-4" />
					{deleting ? "Deleting..." : "Delete"}
				</Button>
				<Button
					type="button"
					size="sm"
					className="h-11"
					onClick={handleSave}
					disabled={mutationsDisabled}
				>
					<Save className="h-4 w-4" />
					{saving ? "Saving..." : "Save policy"}
				</Button>
			</div>
		</section>
	);
}
