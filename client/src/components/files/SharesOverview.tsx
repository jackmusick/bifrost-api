import { useQuery } from "@tanstack/react-query";
import { HardDrive, Lock, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { listShares } from "@/services/fileStructure";
import { InlineLoader } from "./InlineLoader";

export function SharesOverview({
	scope,
	readOnly,
	onSelect,
}: {
	scope: string;
	readOnly: boolean;
	onSelect: (location: string, prefix: string) => void;
}) {
	const shares = useQuery({
		queryKey: ["file-shares", scope],
		queryFn: () => listShares(scope),
		retry: false,
	});
	return (
		<section
			aria-label="Browse shares"
			className="min-h-0 overflow-auto p-1"
		>
			<div className="mb-5 space-y-1">
				<h2 className="text-lg font-semibold">Your shares</h2>
				<p className="text-sm text-muted-foreground">
					Open a share to browse files and folders. Inspect access
					when you need it.
				</p>
			</div>
			{shares.isPending && <InlineLoader label="Loading shares…" />}
			{shares.isError && (
				<div role="alert" className="space-y-3">
					<p className="text-sm">Shares could not be loaded.</p>
					<Button
						variant="outline"
						disabled={shares.isFetching}
						onClick={() => void shares.refetch()}
					>
						Retry shares
					</Button>
				</div>
			)}
			{shares.isSuccess && shares.data.length === 0 && (
				<div className="rounded-[var(--bf-radius-surface)] border border-dashed p-8 text-center">
					<HardDrive className="mx-auto mb-3 size-8 text-muted-foreground" />
					<h3 className="font-medium">No shares in this scope</h3>
					<p className="mt-1 text-sm text-muted-foreground">
						{readOnly
							? "This solution has no file shares."
							: "Create a share to start organizing files, or choose another organization."}
					</p>
				</div>
			)}
			<ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
				{shares.data?.map((share) => (
					<li key={share.location}>
						<button
							type="button"
							onClick={() => onSelect(share.location, "")}
							className="group flex h-full w-full items-start gap-4 rounded-[var(--bf-radius-surface)] border bg-card p-5 text-left transition-colors hover:border-primary/40 hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring motion-reduce:transition-none"
						>
							<span className="flex size-12 shrink-0 items-center justify-center rounded-lg border border-primary/20 bg-primary/10 text-primary">
								<HardDrive className="size-6" />
							</span>
							<span className="min-w-0 space-y-2">
								<span className="block break-all font-semibold">
									{share.location}
								</span>
								<span className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
									{readOnly || share.readOnly ? (
										<>
											<Lock className="size-3.5" />
											Read only
										</>
									) : (
										"File share"
									)}
									{share.hasPolicy && (
										<span className="inline-flex items-center gap-1">
											<ShieldCheck className="size-3.5" />
											Policy configured
										</span>
									)}
								</span>
							</span>
						</button>
					</li>
				))}
			</ul>
		</section>
	);
}
