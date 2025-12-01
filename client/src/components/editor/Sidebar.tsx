import { FileText, Search, Play, Package, GitBranch } from "lucide-react";
import { useEditorStore, type SidebarPanel } from "@/stores/editorStore";
import { cn } from "@/lib/utils";

/**
 * Sidebar with icon navigation for Files, Search, Run, Packages, and Source Control panels
 */
export function Sidebar() {
	const { sidebarPanel, setSidebarPanel } = useEditorStore();

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
		<div className="flex h-full w-12 flex-col border-r bg-muted/30">
			{panels.map((panel) => {
				const Icon = panel.icon;
				const isActive = sidebarPanel === panel.id;

				return (
					<button
						key={panel.id}
						onClick={() => setSidebarPanel(panel.id)}
						className={cn(
							"flex h-12 w-full items-center justify-center transition-colors",
							isActive
								? "bg-muted/50 border-r-2 border-primary"
								: "text-muted-foreground hover:bg-muted/40",
						)}
						title={panel.label}
						aria-label={panel.label}
					>
						<Icon className="h-5 w-5" />
					</button>
				);
			})}
		</div>
	);
}
