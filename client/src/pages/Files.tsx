import { ListPageHeader } from "@/components/layout/ListPageHeader";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { FilesExplorer } from "@/components/files/FilesExplorer";
import { getSolution } from "@/services/solutions";

export function Files() {
	const [searchParams] = useSearchParams();
	const install = searchParams.get("install") ?? undefined;
	const { data: solution } = useQuery({
		queryKey: ["solutions", install],
		queryFn: () => getSolution(install!),
		enabled: Boolean(install),
	});

	return (
		<div className="mx-auto flex h-full min-h-0 w-full max-w-[1600px] flex-col gap-4">
			<ListPageHeader
				className="shrink-0"
				title="Files"
				description={
					install
						? "Browse solution files and inspect their access rules."
						: "Browse shares, manage file policies, and test effective access."
				}
			/>
			<div className="min-h-0 flex-1">
				<FilesExplorer install={install} installName={solution?.name} />
			</div>
		</div>
	);
}
