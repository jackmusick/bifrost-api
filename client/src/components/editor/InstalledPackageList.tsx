import { Loader2, ArrowUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { InstalledPackage, PackageUpdate } from "@/hooks/usePackages";

interface InstalledPackageListProps {
	packages: InstalledPackage[];
	updates: PackageUpdate[];
	isLoading: boolean;
	error: string | null;
	onRetry: () => void;
}

export function InstalledPackageList({
	packages,
	updates,
	isLoading,
	error,
	onRetry,
}: InstalledPackageListProps) {
	return (
		<section aria-label="Installed packages" className="min-w-0">
			<h3 className="border-b bg-muted/30 px-3 py-3 text-xs font-medium text-muted-foreground">
				Installed packages
				{packages.length > 0 ? ` (${packages.length})` : ""}
			</h3>
			{isLoading && (
				<p
					role="status"
					className="flex items-center gap-2 p-3 text-sm text-muted-foreground"
				>
					<Loader2 className="size-4 shrink-0 animate-spin motion-reduce:animate-none" />
					Loading packages…
				</p>
			)}
			{error && (
				<div className="space-y-2 border-b p-3">
					<p role="alert" className="text-sm text-destructive">
						{error}
					</p>
					<Button
						variant="outline"
						className="min-h-11"
						onClick={onRetry}
						disabled={isLoading}
					>
						Retry loading packages
					</Button>
				</div>
			)}
			{!isLoading && !error && packages.length === 0 && (
				<p className="p-4 text-sm text-muted-foreground">
					No packages installed. Install a package or use
					requirements.txt to get started.
				</p>
			)}
			{packages.length > 0 && (
				<ul className="divide-y">
					{packages.map((pkg) => {
						const update = updates.find(
							(item) => item.name === pkg.name,
						);
						return (
							<li
								key={pkg.name}
								className="space-y-1 px-3 py-3 [overflow-wrap:anywhere]"
							>
								<p className="font-medium text-sm">
									{pkg.name}
								</p>
								<p className="text-xs text-muted-foreground">
									Installed{" "}
									<span className="font-mono">
										{pkg.version}
									</span>
								</p>
								{update && (
									<p className="flex items-start gap-1 text-xs text-primary">
										<ArrowUp className="mt-0.5 size-3 shrink-0" />
										<span>
											Update available:{" "}
											<span className="font-mono">
												{update.latest_version}
											</span>
										</span>
									</p>
								)}
							</li>
						);
					})}
				</ul>
			)}
		</section>
	);
}
