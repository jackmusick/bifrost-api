import { useEffect, useRef, useState } from "react";
import { Brain, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { SavedMemoryRecord } from "./SavedMemoryRecord";
import {
	AlertDialog,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { SettingsLoadError } from "@/components/shared/SettingsLoadError";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import {
	getUserMemorySettings,
	listMemories,
	removeMemory,
	updateUserMemorySettings,
	type MemoryEntry,
	type MemoryUserSettings,
} from "@/services/memory";

export function Preferences() {
	const [settings, setSettings] = useState<MemoryUserSettings | null>(null);
	const [memories, setMemories] = useState<MemoryEntry[]>([]);
	const [loading, setLoading] = useState(true);
	const [loadError, setLoadError] = useState(false);
	const [loadAttempt, setLoadAttempt] = useState(0);
	const [saveError, setSaveError] = useState<string | null>(null);
	const [deleteError, setDeleteError] = useState<string | null>(null);
	const [saving, setSaving] = useState(false);
	const [deleting, setDeleting] = useState(false);
	const [deleteCompleted, setDeleteCompleted] = useState(false);
	const [requestedEnabled, setRequestedEnabled] = useState<boolean | null>(
		null,
	);
	const [selectedMemory, setSelectedMemory] = useState<MemoryEntry | null>(
		null,
	);
	const savedMemoriesHeadingRef = useRef<HTMLDivElement>(null);
	const deleteErrorRef = useRef<HTMLParagraphElement>(null);
	const saveErrorRef = useRef<HTMLDivElement>(null);
	const saveBusyRef = useRef(false);
	const deleteBusyRef = useRef(false);
	const dialogFocus = useDialogReturnFocus(
		savedMemoriesHeadingRef,
		deleteCompleted,
	);

	useEffect(() => {
		let active = true;
		Promise.all([getUserMemorySettings(), listMemories()])
			.then(([nextSettings, memoryList]) => {
				if (!active) return;
				setSettings(nextSettings);
				setMemories(memoryList.entries);
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

	useEffect(() => {
		if (deleteError) {
			deleteErrorRef.current?.focus();
			deleteErrorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [deleteError]);

	useEffect(() => {
		if (saveError) {
			saveErrorRef.current?.focus();
			saveErrorRef.current?.scrollIntoView?.({ block: "nearest" });
		}
	}, [saveError]);

	const handleToggle = async (enabled: boolean) => {
		if (
			loading ||
			loadError ||
			!settings ||
			!settings.platform_enabled ||
			saveBusyRef.current
		)
			return;
		saveBusyRef.current = true;
		setRequestedEnabled(enabled);
		setSaveError(null);
		setSaving(true);
		try {
			const nextSettings = await updateUserMemorySettings(enabled);
			setSettings(nextSettings);
			setRequestedEnabled(null);
			toast.success(enabled ? "Memory enabled" : "Memory disabled");
		} catch (error) {
			const message =
				error instanceof Error
					? error.message
					: "Failed to update memory preference";
			setSaveError(message);
		} finally {
			saveBusyRef.current = false;
			setSaving(false);
		}
	};

	const handleDelete = async () => {
		if (!selectedMemory || deleteBusyRef.current) return;
		deleteBusyRef.current = true;
		setDeleteError(null);
		setDeleting(true);
		try {
			await removeMemory(selectedMemory.id);
			setMemories((current) =>
				current.filter((memory) => memory.id !== selectedMemory.id),
			);
			setDeleteCompleted(true);
			setSelectedMemory(null);
			toast.success("Memory removed");
		} catch (error) {
			setDeleteCompleted(false);
			setDeleteError(
				error instanceof Error
					? error.message
					: "Failed to remove memory",
			);
		} finally {
			deleteBusyRef.current = false;
			setDeleting(false);
		}
	};

	return (
		<div className="space-y-6">
			{loadError && (
				<SettingsLoadError
					name="memory preferences"
					onRetry={() => {
						setLoading(true);
						setLoadError(false);
						setLoadAttempt((value) => value + 1);
					}}
				/>
			)}
			<Card>
				<CardHeader>
					<div className="flex items-center gap-2">
						<Brain className="h-5 w-5" />
						<CardTitle>Memory</CardTitle>
					</div>
					<CardDescription>
						Let Bifrost-connected AI assistants use durable, private
						context that you explicitly ask them to remember.
					</CardDescription>
				</CardHeader>
				<CardContent>
					<div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
						<div className="space-y-1">
							<Label htmlFor="user-memory-enabled">
								Enable Memory
							</Label>
							<p className="text-sm text-muted-foreground">
								{settings?.platform_enabled === false
									? "Memory is currently disabled by your platform administrator."
									: "Only your account can search or manage these memories."}
							</p>
						</div>
						<div className="flex items-center gap-2">
							{(loading || saving) && (
								<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none text-muted-foreground" />
							)}
							<Switch
								id="user-memory-enabled"
								checked={settings?.user_enabled ?? false}
								disabled={
									loading ||
									!settings ||
									loadError ||
									saving ||
									settings?.platform_enabled === false
								}
								onCheckedChange={handleToggle}
							/>
						</div>
					</div>
					{saveError && (
						<Alert
							ref={saveErrorRef}
							tabIndex={-1}
							role="alert"
							className="mt-4 rounded-[var(--bf-radius-surface)] border-destructive/30 bg-destructive/5"
						>
							<AlertDescription className="flex flex-col items-start gap-3">
								<span>
									{saveError}. Your memory preference is still
									ready to retry.
								</span>
								<Button
									type="button"
									variant="outline"
									className="min-h-11"
									disabled={saving || loading || loadError}
									onClick={() => {
										if (requestedEnabled !== null) {
											void handleToggle(requestedEnabled);
										}
									}}
								>
									{saving ? "Retrying…" : "Retry save"}
								</Button>
							</AlertDescription>
						</Alert>
					)}
				</CardContent>
			</Card>

			<Card>
				<CardHeader>
					<div
						ref={savedMemoriesHeadingRef}
						tabIndex={-1}
						className="outline-none"
					>
						<CardTitle>Saved Memories</CardTitle>
					</div>
					<CardDescription>
						Review or remove anything Bifrost has remembered for
						you.
					</CardDescription>
				</CardHeader>
				<CardContent>
					{loading ? (
						<div
							role="status"
							className="flex items-center gap-2 text-sm text-muted-foreground"
						>
							<Loader2 className="h-4 w-4 animate-spin motion-reduce:animate-none" />
							Loading memories…
						</div>
					) : loadError && memories.length === 0 ? (
						<p className="text-sm text-muted-foreground">
							Saved memories are unavailable until the connection
							recovers.
						</p>
					) : memories.length === 0 ? (
						<div className="rounded-[var(--bf-radius-surface)] border border-dashed border-border/70 p-8 text-center text-sm text-muted-foreground">
							Nothing has been remembered yet.
						</div>
					) : (
						<div className="max-h-[32rem] space-y-3 overflow-auto pr-1">
							{memories.map((memory) => (
								<SavedMemoryRecord
									key={memory.id}
									memory={memory}
									onRemove={() => {
										setDeleteCompleted(false);
										setDeleteError(null);
										setSelectedMemory(memory);
									}}
								/>
							))}
						</div>
					)}
				</CardContent>
			</Card>

			<AlertDialog
				open={selectedMemory !== null}
				onOpenChange={(open) => {
					if (!open && !deleting) setSelectedMemory(null);
				}}
			>
				<AlertDialogContent
					{...dialogFocus}
					onEscapeKeyDown={(event) => {
						if (deleting) event.preventDefault();
					}}
				>
					<AlertDialogHeader>
						<AlertDialogTitle>Remove this memory?</AlertDialogTitle>
						<AlertDialogDescription>
							Bifrost will no longer be able to find or use it.
						</AlertDialogDescription>
					</AlertDialogHeader>
					{deleteError && (
						<p
							ref={deleteErrorRef}
							tabIndex={-1}
							role="alert"
							className="text-sm text-destructive outline-none"
						>
							Couldn't remove this memory. It is still saved; try
							again.
						</p>
					)}
					<AlertDialogFooter>
						<AlertDialogCancel
							className="min-h-11 lg:min-h-11"
							disabled={deleting}
						>
							Cancel
						</AlertDialogCancel>
						<Button
							type="button"
							disabled={deleting}
							onClick={handleDelete}
							className="min-h-11 bg-destructive text-destructive-foreground hover:bg-destructive/90"
						>
							{deleting
								? "Removing…"
								: deleteError
									? "Retry removal"
									: "Remove"}
						</Button>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
