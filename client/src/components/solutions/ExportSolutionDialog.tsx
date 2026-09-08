import { InstallFailure } from "./InstallSession";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
	Dialog,
	DialogContent,
	DialogDescription,
	DialogFooter,
	DialogHeader,
	DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import type { SolutionExportOptions } from "@/services/solutions";

export interface ExportSolutionDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	/** Called when the user confirms. Presentational — no network calls here. */
	onExport: (
		mode: "shareable" | "full",
		password?: string,
		options?: SolutionExportOptions,
	) => void | Promise<void>;
	/** When true, the Export button is disabled and shows a spinner. */
	isPending?: boolean;
}

/**
 * Presentational dialog for choosing the solution export mode.
 *
 * - "Package" (default): definition only, safe to share.
 * - "Backup": package plus selected runtime state. Selected runtime state is
 *   password-encrypted.
 *
 * Network calls are the caller's responsibility (onExport prop).
 */
export function ExportSolutionDialog(props: ExportSolutionDialogProps) {
	return props.open ? <ExportSession {...props} /> : null;
}

function ExportSession({
	open,
	onOpenChange,
	onExport,
	isPending: externalPending = false,
}: ExportSolutionDialogProps) {
	const busy = useRef(false);
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const returnFocus = useDialogReturnFocus();
	const isPending = externalPending || pending;
	const [mode, setMode] = useState<"shareable" | "full">("shareable");
	const [password, setPassword] = useState("");
	const [includeConfigs, setIncludeConfigs] = useState(true);
	const [includeSecrets, setIncludeSecrets] = useState(false);
	const [includeTables, setIncludeTables] = useState(false);
	const [includeFiles, setIncludeFiles] = useState(true);

	const hasBackupSelection =
		includeConfigs || includeSecrets || includeTables || includeFiles;
	const exportDisabled =
		mode === "full" && (!hasBackupSelection || password.trim() === "");
	const submitLabel =
		mode === "full"
			? isPending
				? "Queueing..."
				: "Queue backup"
			: isPending
				? "Exporting..."
				: "Export";

	async function handleExport() {
		if (busy.current || isPending || exportDisabled) return;
		busy.current = true;
		setPending(true);
		setError(null);
		try {
			await onExport(
				mode,
				mode === "full" ? password : undefined,
				mode === "full"
					? {
							includeConfigs,
							includeSecrets,
							includeTables,
							includeFiles,
						}
					: undefined,
			);
		} catch (err) {
			setError(
				err instanceof Error
					? err.message
					: "Could not export this Solution. Try again.",
			);
		} finally {
			busy.current = false;
			setPending(false);
		}
	}

	function handleOpenChange(next: boolean) {
		if (busy.current || isPending) return;
		if (!next) {
			// Reset state when closing
			setMode("shareable");
			setPassword("");
			setIncludeConfigs(true);
			setIncludeSecrets(false);
			setIncludeTables(false);
			setIncludeFiles(true);
		}
		onOpenChange(next);
	}

	return (
		<Dialog open={open} onOpenChange={handleOpenChange}>
			<DialogContent
				{...returnFocus}
				className="w-[calc(100vw-1rem)] max-h-[92dvh] overflow-y-auto sm:max-w-2xl"
				showCloseButton={!isPending}
				onEscapeKeyDown={(event) => {
					if (isPending) event.preventDefault();
				}}
				onInteractOutside={(event) => {
					if (isPending) event.preventDefault();
				}}
			>
				<DialogHeader>
					<DialogTitle>Export Solution</DialogTitle>
					<DialogDescription>
						Choose how to export this Solution. Definitions, table
						schemas, config declarations, file-location
						declarations, and source files are included in both
						modes.
					</DialogDescription>
				</DialogHeader>

				<fieldset disabled={isPending} className="min-w-0 space-y-4">
					<RadioGroup
						value={mode}
						onValueChange={(v) => {
							setMode(v as "shareable" | "full");
							if (v === "shareable") {
								setPassword("");
								setIncludeConfigs(true);
								setIncludeSecrets(false);
								setIncludeTables(false);
								setIncludeFiles(true);
							}
						}}
						className="grid gap-3 sm:grid-cols-2"
					>
						<label
							htmlFor="mode-shareable"
							className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border p-4 transition-colors motion-reduce:transition-none hover:bg-muted/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-muted/40"
						>
							<RadioGroupItem
								id="mode-shareable"
								value="shareable"
								aria-label="Package"
								className="mt-0.5 shrink-0"
							/>
							<span className="min-w-0">
								<span className="block text-sm font-medium">
									Package
								</span>
								<span className="mt-0.5 block text-xs text-muted-foreground">
									Definitions only. Omits runtime values, file
									payloads, and table rows. Safe to share with
									others or publish.
								</span>
							</span>
						</label>

						<label
							htmlFor="mode-full"
							className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border p-4 transition-colors motion-reduce:transition-none hover:bg-muted/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-muted/40"
						>
							<RadioGroupItem
								id="mode-full"
								value="full"
								aria-label="Backup"
								className="mt-0.5 shrink-0"
							/>
							<span className="min-w-0">
								<span className="block text-sm font-medium">
									Backup
								</span>
								<span className="mt-0.5 block text-xs text-muted-foreground">
									Choose which runtime state to include.
									Backups run in the background, are encrypted
									with a password, and are kept for 7 days.
								</span>
							</span>
						</label>
					</RadioGroup>

					{mode === "full" && (
						<>
							<div className="space-y-1.5">
								<Label htmlFor="export-password">
									Password{" "}
									<span
										className="text-destructive"
										aria-hidden
									>
										*
									</span>
								</Label>
								<Input
									id="export-password"
									type="password"
									required
									value={password}
									onChange={(e) =>
										setPassword(e.target.value)
									}
									placeholder="Set a password for this backup"
									autoComplete="new-password"
								/>
								<p className="text-xs text-muted-foreground">
									You will need this password when installing
									the backup on another instance.
								</p>
							</div>

							<div className="space-y-3 rounded-[var(--bf-radius-control)] border p-3">
								<p className="text-sm font-medium">
									Backup contents
								</p>
								<label
									htmlFor="export-include-configs"
									className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border border-transparent px-3 py-2.5 transition-colors motion-reduce:transition-none hover:bg-muted/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-muted/40"
								>
									<Checkbox
										id="export-include-configs"
										checked={includeConfigs}
										onCheckedChange={(checked) =>
											setIncludeConfigs(checked === true)
										}
										className="mt-0.5 shrink-0"
									/>
									<div className="min-w-0 space-y-0.5">
										<span className="block text-sm font-medium leading-none">
											Config values
										</span>
										<p className="text-xs text-muted-foreground">
											Includes non-secret configured
											values for this install.
										</p>
									</div>
								</label>
								<label
									htmlFor="export-include-secrets"
									className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border border-transparent px-3 py-2.5 transition-colors motion-reduce:transition-none hover:bg-muted/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-muted/40"
								>
									<Checkbox
										id="export-include-secrets"
										checked={includeSecrets}
										onCheckedChange={(checked) =>
											setIncludeSecrets(checked === true)
										}
										className="mt-0.5 shrink-0"
									/>
									<div className="min-w-0 space-y-0.5">
										<span className="block text-sm font-medium leading-none">
											Secrets
										</span>
										<p className="text-xs text-muted-foreground">
											Includes secret config values in the
											encrypted backup.
										</p>
									</div>
								</label>
								<label
									htmlFor="export-include-tables"
									className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border border-transparent px-3 py-2.5 transition-colors motion-reduce:transition-none hover:bg-muted/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-muted/40"
								>
									<Checkbox
										id="export-include-tables"
										checked={includeTables}
										onCheckedChange={(checked) =>
											setIncludeTables(checked === true)
										}
										className="mt-0.5 shrink-0"
									/>
									<div className="min-w-0 space-y-0.5">
										<span className="block text-sm font-medium leading-none">
											Table data
										</span>
										<p className="text-xs text-muted-foreground">
											Adds table rows to the encrypted
											backup payload. Table schemas are
											already included above.
										</p>
									</div>
								</label>
								<label
									htmlFor="export-include-files"
									className="flex min-h-11 cursor-pointer items-start gap-3 rounded-[var(--bf-radius-control)] border border-transparent px-3 py-2.5 transition-colors motion-reduce:transition-none hover:bg-muted/50 has-[[data-state=checked]]:border-primary has-[[data-state=checked]]:bg-muted/40"
								>
									<Checkbox
										id="export-include-files"
										checked={includeFiles}
										onCheckedChange={(checked) =>
											setIncludeFiles(checked === true)
										}
										className="mt-0.5 shrink-0"
									/>
									<div className="min-w-0 space-y-0.5">
										<span className="block text-sm font-medium leading-none">
											Solution-owned files
										</span>
										<p className="text-xs text-muted-foreground">
											Includes file payloads owned by this
											Solution.
										</p>
									</div>
								</label>
								{!hasBackupSelection && (
									<p className="text-xs text-destructive">
										Select at least one backup content type.
									</p>
								)}
							</div>
						</>
					)}
				</fieldset>
				{error && <InstallFailure message={error} />}

				<DialogFooter>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						disabled={isPending}
						onClick={() => handleOpenChange(false)}
					>
						Cancel
					</Button>
					<Button
						type="button"
						className="min-h-11"
						disabled={exportDisabled || isPending}
						onClick={handleExport}
					>
						{isPending && (
							<Loader2 className="mr-1.5 h-4 w-4 animate-spin motion-reduce:animate-none" />
						)}
						{error
							? mode === "full"
								? "Retry backup"
								: "Retry export"
							: submitLabel}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
