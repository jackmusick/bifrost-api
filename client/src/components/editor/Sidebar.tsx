import { FileText, Search, Play, Package, GitBranch } from "lucide-react";
import { useEditorStore, type SidebarPanel } from "@/stores/editorStore";
import { cn } from "@/lib/utils";

/**
 * Sidebar with icon navigation for Files, Search, Run, Packages, and Source Control panels
 */
export function Sidebar() {
	const sidebarPanel = useEditorStore((state) => state.sidebarPanel);
	const setSidebarPanel = useEditorStore((state) => state.setSidebarPanel);

	const panels: Array<{
		id: SidebarPanel;
		icon: typeof FileText;
		label: string;
	}> = [
		{ id: "files", icon: FileText, label: "Files" },
		{ id: "search", icon: Search, label: "Search" },
		{ id: "sourceControl", icon: GitBranch, label: "Source Control" },
		{ id: "run", icon: Play, label: "Run" },
		{ id: "packages", icon: Package, label: "Packages" },
	];

	return (
		<div
			role="group"
			aria-label="Editor tools"
			className="flex h-full w-12 shrink-0 flex-col overflow-y-auto border-r bg-muted/30"
		>
			{panels.map((panel) => {
				const Icon = panel.icon;
				const isActive = sidebarPanel === panel.id;

				return (
					<button
						key={panel.id}
						type="button"
						aria-pressed={isActive}
						onClick={() => setSidebarPanel(panel.id)}
						className={cn(
							"flex h-12 w-full shrink-0 items-center justify-center border-r-2 transition-colors motion-reduce:transition-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring",
							isActive
								? "bg-muted/50 border-primary"
								: "border-transparent text-muted-foreground hover:bg-muted/40",
						)}
						title={panel.label}
						aria-label={panel.label}
					>
						<Icon aria-hidden="true" className="h-5 w-5" />
					</button>
				);
			})}
		</div>
	);
}
