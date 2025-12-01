import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ConflictInfo {
	current_content: string;
	incoming_content: string;
}

interface ConflictResolutionBannerProps {
	conflict: ConflictInfo;
	filePath: string;
	onResolve: (choice: "current" | "incoming" | "both") => void;
}

export function ConflictResolutionBanner({
	conflict,
	onResolve,
}: ConflictResolutionBannerProps) {
	if (!conflict) return null;

	return (
		<div className="bg-orange-500/10 border-b border-orange-500/20 px-4 py-3">
			<div className="flex items-center gap-4">
				<div className="flex items-center gap-2 flex-1">
					<AlertCircle className="h-4 w-4 text-orange-500" />
					<span className="text-sm font-medium">
						This file has a merge conflict
					</span>
				</div>
				<div className="flex items-center gap-2">
					<Button
						size="sm"
						variant="outline"
						onClick={() => onResolve("current")}
						className="border-green-500/20 bg-green-500/10 hover:bg-green-500/20 text-green-700 dark:text-green-400"
					>
						Keep My Changes
					</Button>
					<Button
						size="sm"
						variant="outline"
						onClick={() => onResolve("incoming")}
						className="border-blue-500/20 bg-blue-500/10 hover:bg-blue-500/20 text-blue-700 dark:text-blue-400"
					>
						Keep Their Changes
					</Button>
					<Button
						size="sm"
						variant="outline"
						onClick={() => onResolve("both")}
						className="border-purple-500/20 bg-purple-500/10 hover:bg-purple-500/20 text-purple-700 dark:text-purple-400"
					>
						Keep Both
					</Button>
				</div>
			</div>
		</div>
	);
}
