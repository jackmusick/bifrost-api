import { useState } from "react";
import { Loader2, MessageSquareText, Save } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { $api } from "@/lib/api-client";

export function AIBehaviorSettings() {
	const { data, isLoading, isError, isFetching, refetch } = $api.useQuery("get", "/api/admin/ai/behavior");
	const update = $api.useMutation("put", "/api/admin/ai/behavior");
	const [prompt, setPrompt] = useState("");
	const [dirty, setDirty] = useState(false);
	const [saveError, setSaveError] = useState(false);
	const [loadedData, setLoadedData] = useState<typeof data>(undefined);
	if (data !== loadedData) {
		setLoadedData(data);
		if (!dirty) setPrompt(data?.default_system_prompt ?? "");
	}

	const save = async () => {
		if (!data || update.isPending) return;
		setSaveError(false);
		try {
			await update.mutateAsync({ body: { default_system_prompt: prompt || null } });
			setDirty(false);
			void refetch();
			toast.success("Chat instructions saved");
		} catch {
			setSaveError(true);
		}
	};

	return (
		<div className="min-w-0 w-full space-y-6">
			<div><h2 className="font-display text-2xl font-semibold tracking-tight">Chat instructions</h2><p className="mt-1 text-sm text-muted-foreground">Set the default behavior for agentless conversations. Agent prompts remain configured on each agent.</p></div>
			{isError && <div role="alert" className="space-y-3 rounded-[var(--bf-radius-surface)] border bg-[var(--bf-warning-soft)] p-4 text-sm">
				<p>{data ? "Could not refresh instructions. Your current draft is still available." : "Could not load chat instructions. Retry before editing."}</p>
				<Button variant="outline" className="min-h-11" disabled={isFetching} onClick={() => void refetch()}>{isFetching ? "Retrying…" : "Retry instructions"}</Button>
			</div>}
			<Card className="min-w-0">
				<CardHeader><div className="flex items-start gap-3"><div className="rounded-[var(--bf-radius-control)] bg-muted p-2"><MessageSquareText className="h-4 w-4" /></div><div className="min-w-0"><CardTitle className="text-base">Default system instructions</CardTitle><CardDescription>Applied when a conversation is not using a configured agent.</CardDescription></div></div></CardHeader>
				<CardContent>
					<form className="space-y-4" onSubmit={(event) => { event.preventDefault(); void save(); }}>
					{isLoading && <p role="status" className="text-sm text-muted-foreground">Loading instructions…</p>}
					<div className="space-y-2"><Label htmlFor="default-chat-instructions">Instructions</Label><Textarea id="default-chat-instructions" value={prompt} onChange={(event) => { setPrompt(event.target.value); setDirty(true); setSaveError(false); }} disabled={!data || isLoading || update.isPending} className="min-h-64 text-base leading-relaxed sm:text-sm" placeholder="Describe how the assistant should behave…" /></div>
					{saveError && <p role="alert" className="text-sm text-destructive">Could not save instructions. Your draft is preserved; try again.</p>}
					<div className="flex flex-wrap items-center justify-between gap-3"><p className="text-xs text-muted-foreground">{dirty ? "Unsaved changes" : "Leave blank to use the default instructions."}</p><Button type="submit" className="min-h-11 w-full sm:w-auto" disabled={!data || isLoading || update.isPending}>{update.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" /> : <Save className="mr-2 h-4 w-4" />}Save instructions</Button></div>
				</form>
				</CardContent>
			</Card>
		</div>
	);
}
