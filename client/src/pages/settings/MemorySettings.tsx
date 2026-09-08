import { useEffect, useState } from "react";
import { Brain } from "lucide-react";
import { toast } from "sonner";

import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { SettingsToggleRow } from "@/components/shared/SettingsToggleRow";
import { SettingsLoadError } from "@/components/shared/SettingsLoadError";
import {
	getPlatformMemorySettings,
	updatePlatformMemorySettings,
} from "@/services/memory";

export function MemorySettings() {
	const [enabled, setEnabled] = useState(false);
	const [loading, setLoading] = useState(true);
	const [loadError, setLoadError] = useState(false);
	const [loadAttempt, setLoadAttempt] = useState(0);
	const [saving, setSaving] = useState(false);

	useEffect(() => {
		let active = true;
		getPlatformMemorySettings()
			.then((settings) => {
				if (active) setEnabled(settings.enabled);
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

	const handleChange = async (nextEnabled: boolean) => {
		if (loading || saving || loadError) return;
		setSaving(true);
		try {
			const settings = await updatePlatformMemorySettings(nextEnabled);
			setEnabled(settings.enabled);
			toast.success(
				settings.enabled ? "Memory enabled" : "Memory disabled",
			);
		} catch (error) {
			toast.error(
				error instanceof Error
					? error.message
					: "Failed to update memory settings",
			);
		} finally {
			setSaving(false);
		}
	};

	return (
		<Card>
			<CardHeader>
				<div className="flex items-center gap-2">
					<Brain className="h-5 w-5" />
					<CardTitle>Memory</CardTitle>
				</div>
				<CardDescription>
					Enable private memory for Bifrost-connected AI assistants.
					Configure embeddings in the Embeddings settings.
				</CardDescription>
			</CardHeader>
			<CardContent className="space-y-5">
				{loadError && (
					<SettingsLoadError
						name="memory settings"
						onRetry={() => {
							setLoading(true);
							setLoadError(false);
							setLoadAttempt((value) => value + 1);
						}}
					/>
				)}
				<SettingsToggleRow
					id="platform-memory-enabled"
					label="Enable Memory"
					description="Users can disable memory in their preferences."
					checked={enabled}
					disabled={loading || saving || loadError}
					busy={loading ? "loading" : saving ? "saving" : undefined}
					onChange={handleChange}
				/>
			</CardContent>
		</Card>
	);
}
