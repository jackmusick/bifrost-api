import { useRef, useState, type ComponentProps } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import {
	Dialog,
	DialogContent,
	DialogHeader,
	DialogTitle,
	DialogDescription,
	DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { useDialogReturnFocus } from "@/hooks/useDialogReturnFocus";
import { InstallFailure } from "./InstallSession";
import { UpgradeDiffView } from "./CreateEditSolution";
interface Props {
	name: string;
	version?: string | null;
	open: boolean;
	onClose: () => void;
	onConfirm: () => Promise<unknown>;
	diff?: ComponentProps<typeof UpgradeDiffView>["diff"];
	loading: boolean;
	previewError: boolean;
	retrying: boolean;
	onRetryPreview: () => void;
}
export function SolutionUpdateDialog(props: Props) {
	return props.open ? <UpdateSession {...props} /> : null;
}
function UpdateSession({
	name,
	version,
	onClose,
	onConfirm,
	diff,
	loading,
	previewError,
	retrying,
	onRetryPreview,
}: Props) {
	const busy = useRef(false);
	const [pending, setPending] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const focus = useDialogReturnFocus();
	const confirm = async () => {
		if (busy.current) return;
		busy.current = true;
		setPending(true);
		setError(null);
		try {
			await onConfirm();
		} catch (cause) {
			setError(
				cause instanceof Error
					? cause.message
					: "Update failed. Try again.",
			);
		} finally {
			busy.current = false;
			setPending(false);
		}
	};
	return (
		<Dialog
			open
			onOpenChange={(next) => {
				if (!next && !busy.current) onClose();
			}}
		>
			<DialogContent
				{...focus}
				showCloseButton={!pending}
				data-testid="update-now-dialog"
				className="max-h-[90dvh] overflow-y-auto sm:max-w-xl"
			>
				<DialogHeader>
					<DialogTitle>
						Update {name}
						{version ? ` to v${version}` : ""}?
					</DialogTitle>
					<DialogDescription>
						Pull and redeploy this install from its repository. This
						replaces installed content with the repository’s current
						version.
					</DialogDescription>
				</DialogHeader>
				<div
					data-testid="update-diff"
					className="max-h-[40dvh] overflow-y-auto"
				>
					{loading ? (
						<p
							role="status"
							className="flex items-center gap-2 text-sm text-muted-foreground"
						>
							<Loader2
								aria-hidden="true"
								className="size-4 animate-spin motion-reduce:animate-none"
							/>
							Computing what will change…
						</p>
					) : previewError ? (
						<div className="space-y-3">
							<p
								role="alert"
								className="text-sm text-muted-foreground"
							>
								Could not preview changes. Updating will still
								apply the repository’s current version.
							</p>
							<Button
								variant="outline"
								disabled={pending || retrying}
								onClick={onRetryPreview}
							>
								Retry preview
							</Button>
						</div>
					) : diff ? (
						<UpgradeDiffView diff={diff} />
					) : null}
				</div>
				{error && <InstallFailure message={error} />}
				<DialogFooter>
					<Button
						variant="outline"
						className="min-h-11"
						disabled={pending}
						onClick={onClose}
					>
						Cancel
					</Button>
					<Button
						data-testid="confirm-update-now"
						className="min-h-11"
						disabled={pending}
						onClick={() => void confirm()}
					>
						{pending ? (
							<Loader2
								aria-hidden="true"
								className="size-4 animate-spin motion-reduce:animate-none"
							/>
						) : (
							<RefreshCw aria-hidden="true" className="size-4" />
						)}
						{pending
							? "Updating…"
							: error
								? "Retry update"
								: "Update now"}
					</Button>
				</DialogFooter>
			</DialogContent>
		</Dialog>
	);
}
