import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
export function SolutionUninstallNotice({
	pending,
	error,
	onRetry,
}: {
	pending: boolean;
	error: string | null;
	onRetry: () => void;
}) {
	const ref = useRef<HTMLDivElement>(null);
	useEffect(() => {
		if (error) {
			ref.current?.focus();
			ref.current?.scrollIntoView({ block: "nearest" });
		}
	}, [error]);
	if (!pending && !error) return null;
	return (
		<div
			ref={ref}
			tabIndex={error ? -1 : undefined}
			role={error ? "alert" : "status"}
			className="space-y-3 rounded-[var(--bf-radius-surface)] border border-border bg-card p-[var(--bf-surface-pad)] text-sm"
		>
			<p
				className={
					error
						? "font-medium text-destructive"
						: "flex items-center gap-2 font-medium"
				}
			>
				{pending && (
					<Loader2
						aria-hidden="true"
						className="size-4 animate-spin motion-reduce:animate-none"
					/>
				)}
				{error
					? "Could not uninstall this Solution"
					: "Uninstalling Solution…"}
			</p>
			<p className="text-muted-foreground [overflow-wrap:anywhere]">
				{error ??
					"The install will become inactive. Its data and owned content will be retained."}
			</p>
			{error && (
				<Button
					variant="outline"
					className="min-h-11"
					onClick={onRetry}
				>
					Retry uninstall
				</Button>
			)}
		</div>
	);
}
