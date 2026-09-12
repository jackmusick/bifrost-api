import { useEffect, useRef, useState } from "react";
import { FileText, Loader2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
	Card,
	CardContent,
} from "@/components/ui/card";
import { TiptapEditor } from "@/components/ui/tiptap-editor";
import {
	getRequiredInstructionsSettings,
	updateRequiredInstructionsSettings,
} from "@/services/required-instructions";

interface RequiredInstructionsSettingsProps {
	organizationId?: string;
	embedded?: boolean;
}

export function RequiredInstructionsSettings(props: RequiredInstructionsSettingsProps) {
	return <RequiredInstructionsForm key={props.organizationId ?? "global"} {...props} />;
}

function RequiredInstructionsForm({
	organizationId,
	embedded = false,
}: RequiredInstructionsSettingsProps) {
	const organizationScoped = Boolean(organizationId);
	const title = organizationScoped
		? "Organization Instructions"
		: "Global Instructions";
	const [instructions, setInstructions] = useState("");
	const [savedInstructions, setSavedInstructions] = useState("");
	const [loading, setLoading] = useState(true);
	const [saving, setSaving] = useState(false);
	const [loadError, setLoadError] = useState(false);
	const [saveError, setSaveError] = useState(false);
	const [attempt, setAttempt] = useState(0);
	const activeForm = useRef(true);
	useEffect(() => { activeForm.current = true; return () => { activeForm.current = false; }; }, []);

	useEffect(() => {
		let active = true;
		getRequiredInstructionsSettings(organizationId)
			.then((settings) => {
				if (!active) return;
				setInstructions(settings.instructions);
				setSavedInstructions(settings.instructions);
			})
			.catch(() => { if (active) setLoadError(true); })
			.finally(() => {
				if (active) setLoading(false);
			});
		return () => {
			active = false;
		};
	}, [organizationId, title, attempt]);

	const handleSave = async () => {
		if (loading || saving || loadError) return;
		setSaving(true);
		setSaveError(false);
		try {
			const settings = await updateRequiredInstructionsSettings(
				instructions,
				organizationId,
			);
			if (!activeForm.current) return;
			setInstructions(settings.instructions);
			setSavedInstructions(settings.instructions);
			toast.success(`${title} saved`);
		} catch {
			if (activeForm.current) setSaveError(true);
		} finally {
			if (activeForm.current) setSaving(false);
		}
	};

	const content = (
		<>
			<div className="space-y-1">
				<div className="flex items-center gap-2">
					<FileText className="h-5 w-5" />
					<h3 className="font-display text-xl font-semibold leading-tight tracking-tight">
						{title}
					</h3>
				</div>
				<p className="text-sm text-muted-foreground">
					{organizationScoped
						? "Applied after global instructions for members of this organization."
						: "Applied to every task performed through the default Bifrost MCP endpoint."}
				</p>
			</div>
			{loading ? (
				<div role="status" aria-label={`Loading ${title.toLowerCase()}`} className="flex min-h-[200px] items-center justify-center rounded-[var(--bf-radius-control)] border">
					<Loader2 className="h-5 w-5 animate-spin motion-reduce:animate-none text-muted-foreground" />
				</div>
			) : loadError ? (
				<div role="alert" className="space-y-3 rounded-[var(--bf-radius-control)] bg-[var(--bf-warning-soft)] p-4 text-sm">
					<p>Could not load {title.toLowerCase()}. Retry before editing.</p>
					<Button variant="outline" className="min-h-11" onClick={() => { setLoading(true); setLoadError(false); setAttempt(value => value + 1); }}>Retry instructions</Button>
				</div>
			) : (
				<TiptapEditor
					content={instructions}
					readOnly={saving}
					onChange={setInstructions}
					placeholder="Add instructions in Markdown..."
					ariaLabel={`${title} editor`}
					editorClassName="min-h-[220px]"
				/>
			)}
			{saveError && <p role="alert" className="text-sm text-destructive">Could not save instructions. Your draft is preserved; try again.</p>}
			<div className="flex flex-wrap justify-end gap-3">
				<Button
					onClick={handleSave}
					className="min-h-11 w-full sm:w-auto"
					disabled={loadError || loading || saving || instructions === savedInstructions}
				>
					{saving && <Loader2 className="mr-2 h-4 w-4 animate-spin motion-reduce:animate-none" />}
					Save Instructions
				</Button>
			</div>
		</>
	);

	if (embedded) {
		return <div className="min-w-0 space-y-4">{content}</div>;
	}

	return (
		<Card className="min-w-0">
			<CardContent className="space-y-4 pt-6">{content}</CardContent>
		</Card>
	);
}
