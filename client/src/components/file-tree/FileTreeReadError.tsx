import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function FileTreeReadError({
	paths,
	loading,
	onRetry,
}: {
	paths: string[];
	loading: boolean;
	onRetry: () => void;
}) {
	return (
		<Alert variant="destructive">
			<AlertTitle>Could not load files</AlertTitle>
			<AlertDescription>
				<ul
					aria-label="Locations that failed to load"
					tabIndex={0}
					className="max-h-40 overflow-auto space-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
				>
					{paths.map((path) => (
						<li key={path} className="[overflow-wrap:anywhere]">
							{path || "Root folder"}
						</li>
					))}
				</ul>
				<Button
					type="button"
					variant="outline"
					className="mt-3 min-h-11 h-auto whitespace-normal"
					disabled={loading}
					onClick={onRetry}
				>
					{loading ? "Retrying…" : "Retry loading files"}
				</Button>
			</AlertDescription>
		</Alert>
	);
}
