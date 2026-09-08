import { useEffect, useRef, useState } from "react";
import { Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { SettingsToggleRow } from "@/components/shared/SettingsToggleRow";
import { SettingsLoadError } from "@/components/shared/SettingsLoadError";
import {
	cleanupExpiredArtifacts,
	getArtifactRetentionSettings,
	updateArtifactRetentionSettings,
} from "@/services/artifactRetention";

export function ArtifactRetentionSettings() {
	const [enabled, setEnabled] = useState(false);
	const [retentionDays, setRetentionDays] = useState("90");
	const [loading, setLoading] = useState(true);
	const [loadError, setLoadError] = useState(false);
	const [loadAttempt, setLoadAttempt] = useState(0);
	const [saving, setSaving] = useState(false);
	const [cleaning, setCleaning] = useState(false);
	const [validationError, setValidationError] = useState(false);
	const [failedSave, setFailedSave] = useState<{
		enabled: boolean;
		days: string;
	} | null>(null);
	const [cleanupError, setCleanupError] = useState(false);
	const savePending = useRef(false);

	useEffect(() => {
		let active = true;
		getArtifactRetentionSettings()
			.then((settings) => {
				if (!active) return;
				setEnabled(settings.enabled);
				setRetentionDays(String(settings.retention_days));
			})
			.catch(() => {
				if (active) setLoadError(true);
			})
			.finally(() => {
				if (active) setLoading(false);
			});
		return () => {
			active = false;
		};
	}, [loadAttempt]);

	const saveSettings = async (
		nextEnabled = enabled,
		nextDays = retentionDays,
	) => {
		if (loading || savePending.current || loadError) return;
		if (!nextDays.trim() || !Number.isFinite(Number(nextDays))) {
			setValidationError(true);
			return;
		}
		setValidationError(false);
		savePending.current = true;
		setFailedSave(null);
		setSaving(true);
		const normalizedDays = Math.max(
			1,
			Math.min(3650, Math.round(Number(nextDays))),
		);
		try {
			const settings = await updateArtifactRetentionSettings({
				enabled: nextEnabled,
				retention_days: normalizedDays,
			});
			setEnabled(settings.enabled);
			setRetentionDays(String(settings.retention_days));
			toast.success("Artifact retention saved");
		} catch {
			setFailedSave({ enabled: nextEnabled, days: nextDays });
		} finally {
			savePending.current = false;
			setSaving(false);
		}
	};

	const handleCleanup = async () => {
		if (
			loading ||
			savePending.current ||
			cleaning ||
			loadError ||
			validationError ||
			failedSave
		)
			return;
		if (!retentionDays.trim() || !Number.isFinite(Number(retentionDays))) {
			setValidationError(true);
			return;
		}
		setCleanupError(false);
		setCleaning(true);
		try {
			const result = await cleanupExpiredArtifacts();
			toast.success(
				result.reused
					? "Artifact cleanup already queued"
					: "Artifact cleanup queued",
				{
					description: "Progress is available in notifications.",
				},
			);
		} catch {
			setCleanupError(true);
		} finally {
			setCleaning(false);
		}
	};

	return (
		<Card>
			<CardHeader>
				<CardTitle>Artifact Retention</CardTitle>
				<CardDescription>
					Set how long Chat attachments and generated artifacts are
					retained.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-5">
				{loadError && (
					<SettingsLoadError
						name="artifact retention settings"
						onRetry={() => {
							setLoading(true);
							setLoadError(false);
							setLoadAttempt((value) => value + 1);
						}}
					/>
				)}
				<SettingsToggleRow
					id="artifact-retention-enabled"
					label="Enable Scheduled Cleanup"
					description="Expired Chat files are removed during the daily maintenance window."
					checked={enabled}
					disabled={loading || saving || loadError}
					busy={loading ? "loading" : saving ? "saving" : undefined}
					onChange={(checked) => void saveSettings(checked)}
				/>

				<div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
					<div className="space-y-2">
						<Label htmlFor="artifact-retention-days">
							Retention Days
						</Label>
						<Input
							id="artifact-retention-days"
							type="number"
							min={1}
							max={3650}
							value={retentionDays}
							disabled={loading || saving || loadError}
							onChange={(event) => {
								setRetentionDays(event.target.value);
								setValidationError(false);
							}}
							aria-invalid={validationError}
							aria-describedby="retention-days-help"
							onBlur={() => void saveSettings()}
							className="min-h-11 w-full sm:w-32"
						/>
						<p
							id="retention-days-help"
							className="text-xs text-muted-foreground"
						>
							Enter 1–3,650 days. Changes save when you leave the
							field.
						</p>
						{validationError && (
							<p
								role="alert"
								className="text-sm text-destructive"
							>
								Enter a number of days before saving.
							</p>
						)}
					</div>
					<Button
						type="button"
						variant="outline"
						className="min-h-11"
						onClick={handleCleanup}
						disabled={
							loading ||
							saving ||
							cleaning ||
							loadError ||
							validationError ||
							failedSave !== null
						}
					>
						{cleaning ? (
							<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
						) : (
							<Trash2 className="h-4 w-4 mr-2" />
						)}
						{cleanupError ? "Retry Cleanup" : "Run Cleanup"}
					</Button>
				</div>
				{failedSave && (
					<div role="alert" className="space-y-3">
						<p className="text-sm text-destructive">
							Couldn't save retention settings. Your edit is ready
							to retry.
						</p>
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
							onClick={() =>
								void saveSettings(
									failedSave.enabled,
									retentionDays,
								)
							}
						>
							Retry save
						</Button>
					</div>
				)}
				{cleanupError && (
					<p role="alert" className="text-sm text-destructive">
						Couldn't queue cleanup. Try again.
					</p>
				)}
			</CardContent>
		</Card>
	);
}
