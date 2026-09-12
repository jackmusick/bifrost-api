import { useEffect, useRef } from "react";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogDescription,
	DialogFooter,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";

export function GitHubCreateRepositoryDialog({
	open,
	name,
	description,
	isPrivate,
	pending,
	failed,
	onClose,
	onConfirm,
	onNameChange,
	onDescriptionChange,
	onPrivateChange,
}: {
	open: boolean;
	name: string;
	description: string;
	isPrivate: boolean;
	pending: boolean;
	failed: boolean;
	onClose: () => void;
	onConfirm: () => void;
	onNameChange: (value: string) => void;
	onDescriptionChange: (value: string) => void;
	onPrivateChange: (value: boolean) => void;
}) {
	const focus = useDialogReturnFocus();
	const failedRef = useRef<HTMLParagraphElement>(null);

	useEffect(() => {
		if (!open || !failed) return;
		failedRef.current?.focus();
		failedRef.current?.scrollIntoView({ block: "nearest" });
	}, [failed, open]);

	return (
		<Dialog
			open={open}
			onOpenChange={(next) => {
				if (!next && !pending) onClose();
			}}
		>
			<DialogContent
				{...focus}
				className="flex max-h-[90dvh] flex-col overflow-hidden"
				onOpenAutoFocus={(event) => {
					focus.onOpenAutoFocus();
					if (failed) {
						event.preventDefault();
						failedRef.current?.focus();
					}
				}}
				onEscapeKeyDown={(e) => {
					if (pending) e.preventDefault();
				}}
				onPointerDownOutside={(e) => {
					if (pending) e.preventDefault();
				}}
			>
				<DialogHeader className="shrink-0">
					<DialogTitle>Create New Repository</DialogTitle>
					<DialogDescription>
						Create a new GitHub repository in your account
					</DialogDescription>
				</DialogHeader>

				<div className="min-h-0 flex-1 overflow-y-auto py-4">
					<fieldset
						disabled={pending}
						className="min-w-0 space-y-4 [&_input:not([type=checkbox])]:min-h-11"
					>
						<div className="space-y-2">
							<Label htmlFor="new-repo-name">Repository Name</Label>
							<Input
								id="new-repo-name"
								placeholder="my-repository"
								value={name}
								onChange={(e) => onNameChange(e.target.value)}
							/>
						</div>

						<div className="space-y-2">
							<Label htmlFor="new-repo-desc">
								Description (Optional)
							</Label>
							<Input
								id="new-repo-desc"
								placeholder="A brief description"
								value={description}
								onChange={(e) =>
									onDescriptionChange(e.target.value)
								}
							/>
						</div>

						<div className="flex items-center space-x-2">
							<Switch
								id="new-repo-private"
								checked={isPrivate}
								onCheckedChange={(checked) =>
									onPrivateChange(checked === true)
								}
								disabled={pending}
							/>
							<Label
								htmlFor="new-repo-private"
								className="min-h-11 cursor-pointer text-sm font-normal"
							>
								Private repository
							</Label>
						</div>
					</fieldset>

					{failed && (
						<p
							ref={failedRef}
							role="alert"
							tabIndex={-1}
							className="mt-4 rounded-[var(--bf-radius-surface)] border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive outline-none [overflow-wrap:anywhere]"
						>
							Could not create repository. Your details are still
							here. Try again.
						</p>
					)}
				</div>

				<DialogFooter className="shrink-0 border-t pt-4 [&>button]:min-h-11">
					<Button
						variant="outline"
						onClick={onClose}
						disabled={pending}
					>
						Cancel
					</Button>
					<Button
						onClick={onConfirm}
						disabled={!name.trim() || pending}
					>
						{pending ? (
							<>
								<Loader2 className="h-4 w-4 mr-2 animate-spin motion-reduce:animate-none" />
								Creating...
							</>
						) : (
							"Create Repository"
						)}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
