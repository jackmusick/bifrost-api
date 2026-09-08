import {
	AlertDialog,
	AlertDialogCancel,
	AlertDialogContent,
	AlertDialogDescription,
	AlertDialogFooter,
	AlertDialogHeader,
	AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import type { components } from "@/lib/v1";

export type PublicAction = "publish" | "rotate" | "unpublish" | null;
interface FormPublicationReviewDialogProps {
	action: PublicAction;
	review: components["schemas"]["FormPublicationReview"] | null;
	pending: boolean;
	error: boolean;
	onClose: () => void;
	onConfirm: () => void;
}
export function FormPublicationReviewDialog({
	action,
	review,
	pending,
	error,
	onClose,
	onConfirm,
}: FormPublicationReviewDialogProps) {
	const providerFields = review?.provider_fields || [];
	const fileFields = review?.file_fields || [];
	const warnings = review?.warnings || [];
	return (
		<AlertDialog
			open={action !== null}
			onOpenChange={(nextOpen) => {
				if (!nextOpen && !pending) onClose();
			}}
		>
			<AlertDialogContent className="p-[var(--bf-surface-pad)] [overflow-wrap:anywhere]">
				<AlertDialogHeader className="place-items-start gap-3 text-left">
					<AlertDialogTitle>
						{action === "rotate"
							? "Rotate the public embed code?"
							: action === "unpublish"
								? "Disable the public embed?"
								: "Allow anonymous form access?"}
					</AlertDialogTitle>
					<AlertDialogDescription asChild>
						<div className="space-y-3">
							{action !== "rotate" && action !== "unpublish" ? (
								<>
									<p>
										Anyone on an allowed website can load
										this form without signing in. The public
										session can only use the capabilities
										below.
									</p>
									<ul className="list-disc space-y-1 pl-5 text-left">
										<li>
											Execute{" "}
											{review?.submission_workflow
												?.name ||
												"the linked submission workflow"}
											.
										</li>
										{review?.startup_workflow ? (
											<li>
												Load data from{" "}
												{review.startup_workflow.name}{" "}
												when the form opens.
											</li>
										) : null}
										{providerFields.length > 0 ? (
											<li>
												Query {providerFields.length}{" "}
												approved data provider
												{providerFields.length === 1
													? ""
													: "s"}
												:{" "}
												{providerFields
													.map(
														(field) =>
															field.provider_name,
													)
													.join(", ")}
												.
											</li>
										) : null}
										{fileFields.length > 0 ? (
											<li>
												Upload files for:{" "}
												{fileFields.join(", ")}.
											</li>
										) : null}
									</ul>
									{warnings.map((warning) => (
										<p
											key={warning}
											className="text-[var(--bf-warning)]"
										>
											{warning}
										</p>
									))}
									<p className="font-medium text-foreground">
										No other workflows or Bifrost execution
										APIs are granted.
									</p>
								</>
							) : action === "rotate" ? (
								<p>
									Existing embed code stops loading
									immediately. Replace it on every website
									with the newly generated code.
								</p>
							) : (
								<p>
									The public iframe and issued public sessions
									stop working immediately. The private link
									and HMAC integrations are unaffected.
								</p>
							)}
						</div>
					</AlertDialogDescription>
				</AlertDialogHeader>
				{error && (
					<p role="alert" className="text-sm text-destructive">
						Could not update public access. Your review is still
						open; try again.
					</p>
				)}
				{pending && (
					<p role="status" className="text-sm text-muted-foreground">
						Updating public access…
					</p>
				)}
				<AlertDialogFooter>
					<AlertDialogCancel
						disabled={pending}
						className="min-h-11 lg:min-h-11"
					>
						Cancel
					</AlertDialogCancel>
					<Button
						type="button"
						variant={action === "publish" ? "default" : "destructive"}
						className="min-h-11"
						disabled={pending}
						onClick={onConfirm}
					>
						{pending
							? "Updating…"
							: action === "rotate"
								? "Rotate"
								: action === "unpublish"
									? "Disable embed"
									: "Publish public embed"}
					</Button>
				</AlertDialogFooter>
			</AlertDialogContent>
		</AlertDialog>
	);
}
