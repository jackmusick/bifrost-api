import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
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
import { saveFilePolicy } from "@/services/filePolicies";

interface NewShareDialogProps {
	open: boolean;
	onOpenChange: (open: boolean) => void;
	scope: string | null;
	onCreated: (location: string) => void;
}

// Reserved/blocked names the explorer never creates as shares.
const RESERVED = new Set([
	"workspace",
	"uploads",
	"temp",
	"_repo",
	"_tmp",
	"_apps",
]);
const NAME_PATTERN = /^[a-z0-9][a-z0-9-]*$/;

function NewShareSession({
	open,
	onOpenChange,
	scope,
	onCreated,
}: NewShareDialogProps) {
	const [name, setName] = useState("");
	const [error, setError] = useState<string | null>(null);
	const [saving, setSaving] = useState(false);
	const inFlight = useRef(false);
	const errorRef = useRef<HTMLParagraphElement>(null);
	useEffect(() => {
		if (error) {
			errorRef.current?.focus();
			errorRef.current?.scrollIntoView({ block: "nearest" });
		}
	}, [error]);

	function validate(value: string): string | null {
		const trimmed = value.trim();
		if (!trimmed) return "Enter a share name.";
		if (RESERVED.has(trimmed)) return `'${trimmed}' is a reserved name.`;
		if (!NAME_PATTERN.test(trimmed))
			return "Use lowercase letters, numbers, and hyphens.";
		return null;
	}

	async function handleCreate() {
		if (inFlight.current) return;
		const trimmed = name.trim();
		const validationError = validate(trimmed);
		if (validationError) {
			setError(validationError);
			return;
		}
		inFlight.current = true;
		setSaving(true);
		setError(null);
		try {
			// Create the first policy (empty doc → backend seeds admin_bypass).
			await saveFilePolicy({
				location: trimmed,
				path: "",
				organizationId: scope,
				policies: { policies: [] },
			});
			toast.success(`Share '${trimmed}' created`);
			onCreated(trimmed);
			onOpenChange(false);
			setName("");
		} catch (err) {
			setError(err instanceof Error ? err.message : String(err));
		} finally {
			inFlight.current = false;
			setSaving(false);
		}
	}

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!inFlight.current) onOpenChange(next);
			}}
		>
			<DialogContent
				className="flex max-h-[90dvh] flex-col overflow-hidden p-0 sm:max-w-md [&_[data-slot=dialog-header]]:pr-16"
				showCloseButton={!saving}
				onEscapeKeyDown={(event) => {
					if (inFlight.current) event.preventDefault();
				}}
				onInteractOutside={(event) => {
					if (inFlight.current) event.preventDefault();
				}}
			>
				<form
					className="flex min-h-0 flex-1 flex-col"
					onSubmit={(event) => {
						event.preventDefault();
						void handleCreate();
					}}
				>
					<DialogHeader className="shrink-0 border-b p-5">
						<DialogTitle>New share</DialogTitle>
						<DialogDescription>
							Create a place to store files and manage who can
							access them.
						</DialogDescription>
					</DialogHeader>
					<div className="min-h-0 flex-1 space-y-2 overflow-y-auto p-5">
						<Label htmlFor="new-share-name">Share name</Label>
						<Input
							id="new-share-name"
							value={name}
							disabled={saving}
							autoComplete="off"
							spellCheck={false}
							aria-invalid={!!error}
							aria-describedby={
								error
									? "new-share-hint new-share-error"
									: "new-share-hint"
							}
							placeholder="reports"
							onChange={(event) => {
								setName(event.target.value);
								setError(null);
							}}
						/>
						{error && (
							<p
								ref={errorRef}
								tabIndex={-1}
								id="new-share-error"
								role="alert"
								className="text-sm text-destructive outline-none [overflow-wrap:anywhere]"
							>
								{error}
							</p>
						)}
						<p
							id="new-share-hint"
							className="text-sm text-muted-foreground [overflow-wrap:anywhere]"
						>
							Use lowercase letters, numbers, and hyphens.
							Administrators can grant access after creation.
							Files are stored under{" "}
							<span className="font-mono">
								{name.trim() || "name"}/
							</span>
							.
						</p>
					</div>
					<DialogFooter className="shrink-0 border-t p-4">
						<Button
							type="button"
							variant="outline"
							className="min-h-11"
							disabled={saving}
							onClick={() => onOpenChange(false)}
						>
							Cancel
						</Button>
						<Button
							type="submit"
							className="min-h-11"
							disabled={saving}
						>
							{saving ? "Creating…" : "Create share"}
						</Button>
					</DialogFooter>
					{saving && (
						<p
							role="status"
							className="shrink-0 px-4 pb-3 text-sm text-muted-foreground"
						>
							Creating share…
						</p>
					)}
				</form>
			</DialogContent>
		</Dialog>
	);
}

export function NewShareDialog(props: NewShareDialogProps) {
	if (!props.open) return null;
	return <NewShareSession key={props.scope ?? "global"} {...props} />;
}
