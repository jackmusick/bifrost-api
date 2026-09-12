import { useMemo, useRef, useState } from "react";
import { Database, Loader2, Save } from "lucide-react";
import { toast } from "sonner";

import { ProviderModelField } from "@/components/ai/ProviderModelField";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
	AlertDialog,
	AlertDialogAction,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import {
	Select,
	SelectContent,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "@/components/ui/select";
import { $api } from "@/lib/api-client";

export function AIEmbeddingSettings() {
	const { data: connections = [], isLoading: loadingConnections, isError: connectionsError, isFetching: fetchingConnections, refetch: refetchConnections } =
		$api.useQuery("get", "/api/admin/ai/connections");
	const {
		data: config,
		isLoading: loadingConfig,
		isError: configError,
		isFetching: fetchingConfig,
		refetch,
	} = $api.useQuery("get", "/api/admin/llm/embedding-config");
	const saveEmbedding = $api.useMutation(
		"post",
		"/api/admin/llm/embedding-config",
	);
	const [connectionId, setConnectionId] = useState("");
	const [model, setModel] = useState("");
	const [confirmReindex, setConfirmReindex] = useState(false);
	const [dirty, setDirty] = useState(false);
	const [saveError, setSaveError] = useState(false);
	const [saving, setSaving] = useState(false);
	const saveBusy = useRef(false);
	const [loadedConfig, setLoadedConfig] = useState<typeof config>(undefined);
	const compatibleConnections = useMemo(
		() =>
			connections.filter(
				(connection) =>
					connection.provider === "openai" ||
					connection.provider === "openrouter" ||
					connection.provider === "openai_compatible",
			),
		[connections],
	);

	if (config !== loadedConfig) {
		setLoadedConfig(config);
		if (!dirty) {
			setConnectionId(config?.connection_id ?? "");
			setModel(config?.model ?? "");
		}
	}

	const save = async (confirmed = false) => {
		if (!connectionId || !model.trim() || saveBusy.current || connectionsError || configError) return;
		saveBusy.current = true;
		setSaving(true);
		setSaveError(false);
		try {
			const result = await saveEmbedding.mutateAsync({
				body: {
					connection_id: connectionId,
					model: model.trim(),
					confirm_reindex: confirmed,
				},
			});
			if (result.needs_reindex_confirmation) {
				setConfirmReindex(true);
				return;
			}
			setConfirmReindex(false);
			setDirty(false);
			await refetch();
			toast.success(
				result.notification_id
					? "Embedding configuration saved; reindexing has started"
					: "Embedding configuration saved",
			);
		} catch {
			setSaveError(true);
		} finally {
			saveBusy.current = false;
			setSaving(false);
		}
	};

	const loading = loadingConnections || loadingConfig;
	return (
		<div className="min-w-0 w-full space-y-6">
			<div>
				<h2 className="font-display text-2xl font-semibold tracking-tight">
					Embeddings
				</h2>
				<p className="mt-1 text-sm text-muted-foreground">
					Choose a provider connection and model directly. Embeddings
					stay separate from reusable chat and agent profiles.
				</p>
			</div>
			<Card>
				<CardHeader>
					<div className="flex items-start gap-3">
						<div className="rounded-[var(--bf-radius-control)] bg-muted p-2">
							<Database className="h-4 w-4" />
						</div>
						<div>
							<CardTitle className="text-base">
								Knowledge embeddings
							</CardTitle>
							<CardDescription>
								Changing models may require re-embedding
								existing knowledge.
							</CardDescription>
						</div>
					</div>
				</CardHeader>
				<CardContent className="space-y-5">
					{loading && <p role="status" className="text-sm text-muted-foreground">Loading embedding settings…</p>}
					{(connectionsError || configError) && <div role="alert" className="space-y-3 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-4 text-sm"><p>Could not load the latest embedding settings. Your current selections are preserved.</p><Button variant="outline" className="min-h-11" disabled={fetchingConnections || fetchingConfig} onClick={() => { void refetchConnections(); void refetch(); }}>Retry settings</Button></div>}
					<fieldset disabled={loading || saving || confirmReindex || connectionsError || configError} className="min-w-0 space-y-5">
					{compatibleConnections.length === 0 && !loading && !connectionsError && (
						<Alert>
							<AlertTitle>
								No compatible provider connection
							</AlertTitle>
							<AlertDescription>
								Add an OpenAI, OpenRouter, or OpenAI-compatible
								connection first.
							</AlertDescription>
						</Alert>
					)}
					<div className="space-y-2">
						<Label htmlFor="embedding-connection">
							Provider connection
						</Label>
						<Select
							value={connectionId}
							onValueChange={(nextConnectionId) => {
								setDirty(true);
								setConnectionId(nextConnectionId);
								if (nextConnectionId !== connectionId)
									setModel("");
							}}
							disabled={loading || saving || confirmReindex || connectionsError || configError}
						>
							<SelectTrigger id="embedding-connection" className="h-auto data-[size=default]:h-auto min-h-11 w-full whitespace-normal [&_[data-slot=select-value]]:whitespace-normal [&_[data-slot=select-value]]:text-left [&_[data-slot=select-value]]:[overflow-wrap:anywhere]">
								<SelectValue placeholder="Select a connection" />
							</SelectTrigger>
							<SelectContent>
								{compatibleConnections.map((connection) => (
									<SelectItem
										key={connection.id}
										value={connection.id}
									>
										{connection.name} ·{" "}
										{connection.provider}
									</SelectItem>
								))}
							</SelectContent>
						</Select>
					</div>
					<ProviderModelField
						id="embedding-model"
						disabled={loading || saving || confirmReindex || connectionsError || configError}
						connectionId={connectionId}
						value={model}
						onValueChange={(value) => { setDirty(true); setModel(value); }}
					/>
					{saveError && !confirmReindex && <p role="alert" className="text-sm text-destructive">Could not save embeddings. Your selections are preserved; try again.</p>}
					<div className="flex justify-end">
						<Button
							className="min-h-11 w-full sm:w-auto"
						onClick={() => void save()}
							disabled={
								!connectionId ||
								!model.trim() ||
								saving
							}
						>
							{saving ? (
								<Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />
							) : (
								<Save className="mr-2 h-4 w-4" />
							)}
							Save embeddings
						</Button>
					</div>
				</fieldset>
				</CardContent>
			</Card>
			<AlertDialog open={confirmReindex} onOpenChange={(open) => { if (!saving) setConfirmReindex(open); }}>
				<AlertDialogContent>
					<AlertDialogHeader>
						<AlertDialogTitle>
							Re-embed existing knowledge?
						</AlertDialogTitle>
						<AlertDialogDescription>
							This model is incompatible with some stored vectors.
							Saving will start a background reindex so knowledge
							search remains accurate.
						</AlertDialogDescription>
					</AlertDialogHeader>
					{saveError && <p role="alert" className="text-sm text-destructive">Could not save and reindex. Your selections are preserved; try again.</p>}
					<AlertDialogFooter>
						<AlertDialogCancel disabled={saving} className="min-h-11">Cancel</AlertDialogCancel>
						<AlertDialogAction disabled={saving} className="min-h-11" onClick={(event) => { event.preventDefault(); void save(true); }}>
							{saving ? "Saving…" : "Save and reindex"}
						</AlertDialogAction>
					</AlertDialogFooter>
				</AlertDialogContent>
			</AlertDialog>
		</div>
	);
}
