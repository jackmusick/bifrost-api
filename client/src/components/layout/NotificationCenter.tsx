import { useState } from "react";
import {
	Bell,
	X,
	AlertCircle,
	AlertTriangle,
	Info,
	CheckCircle,
	Trash2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
	Popover,
	PopoverContent,
	PopoverTrigger,
} from "@/components/ui/popover";
import {
	useNotificationStore,
	getNotificationCounts,
	type Notification,
	type NotificationStatus,
} from "@/stores/notificationStore";
import { useEditorStore } from "@/stores/editorStore";
import { fileService } from "@/services/fileService";
import { cn } from "@/lib/utils";

/**
 * Notification Center component for the header
 *
 * Displays a bell icon with badge count and a dropdown with notifications.
 * Supports linking to files in the code editor.
 */

const statusConfig: Record<
	NotificationStatus,
	{ icon: typeof AlertCircle; color: string; bgColor: string }
> = {
	error: {
		icon: AlertCircle,
		color: "text-red-500",
		bgColor: "bg-red-500/10",
	},
	warning: {
		icon: AlertTriangle,
		color: "text-yellow-500",
		bgColor: "bg-yellow-500/10",
	},
	info: {
		icon: Info,
		color: "text-blue-500",
		bgColor: "bg-blue-500/10",
	},
	success: {
		icon: CheckCircle,
		color: "text-green-500",
		bgColor: "bg-green-500/10",
	},
};

function NotificationItem({
	notification,
	onDismiss,
	onNavigate,
}: {
	notification: Notification;
	onDismiss: () => void;
	onNavigate: () => void;
}) {
	const config = statusConfig[notification.status];
	const Icon = config.icon;

	return (
		<div
			className={cn(
				"flex items-start gap-3 p-3 rounded-lg border",
				config.bgColor,
			)}
		>
			<Icon
				className={cn("h-5 w-5 mt-0.5 flex-shrink-0", config.color)}
			/>
			<div className="flex-1 min-w-0">
				{notification.link ? (
					<button
						onClick={onNavigate}
						className="text-sm font-medium hover:underline text-left w-full truncate block"
					>
						{notification.title}
					</button>
				) : (
					<span className="text-sm font-medium truncate block">
						{notification.title}
					</span>
				)}
				<p className="text-xs text-muted-foreground mt-1">
					{notification.body}
				</p>
				<p className="text-xs text-muted-foreground/60 mt-1">
					{new Date(notification.createdAt).toLocaleString()}
				</p>
			</div>
			<Button
				variant="ghost"
				size="icon"
				className="h-6 w-6 flex-shrink-0"
				onClick={onDismiss}
			>
				<X className="h-3 w-3" />
			</Button>
		</div>
	);
}

export function NotificationCenter() {
	const [isOpen, setIsOpen] = useState(false);
	const notifications = useNotificationStore((state) => state.notifications);
	const removeNotification = useNotificationStore(
		(state) => state.removeNotification,
	);
	const clearAll = useNotificationStore((state) => state.clearAll);
	const openFileInTab = useEditorStore((state) => state.openFileInTab);
	const openEditor = useEditorStore((state) => state.openEditor);
	const setLoadingFile = useEditorStore((state) => state.setLoadingFile);

	const counts = getNotificationCounts(notifications);

	// Sort: errors first, then warnings, then info, then success
	const sortedNotifications = [...notifications].sort((a, b) => {
		const priority: Record<NotificationStatus, number> = {
			error: 0,
			warning: 1,
			info: 2,
			success: 3,
		};
		return priority[a.status] - priority[b.status];
	});

	const handleNavigate = async (notification: Notification) => {
		if (notification.link) {
			// Close the popover
			setIsOpen(false);

			// Open the editor and navigate to the file
			openEditor();
			try {
				setLoadingFile(true);
				// Fetch file content and open in tab
				const response = await fileService.readFile(notification.link);
				openFileInTab(
					{
						path: notification.link,
						name:
							notification.link.split("/").pop() ||
							notification.link,
						type: "file",
						size: null,
						extension: notification.link.split(".").pop() || null,
						modified: new Date().toISOString(),
						isReadOnly: false,
					},
					response.content,
					response.encoding as "utf-8" | "base64",
					response.etag,
				);
			} catch (error) {
				console.error("Failed to open file:", error);
			} finally {
				setLoadingFile(false);
			}
		}
	};

	// Badge color based on highest priority notification
	const getBadgeVariant = () => {
		if (counts.error > 0) return "destructive";
		if (counts.warning > 0) return "default";
		return "secondary";
	};

	return (
		<Popover open={isOpen} onOpenChange={setIsOpen}>
			<PopoverTrigger asChild>
				<Button variant="ghost" size="icon" className="relative">
					<Bell className="h-4 w-4" />
					{counts.total > 0 && (
						<Badge
							variant={getBadgeVariant()}
							className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
						>
							{counts.total > 99 ? "99+" : counts.total}
						</Badge>
					)}
				</Button>
			</PopoverTrigger>
			<PopoverContent className="w-96 p-0" align="end" sideOffset={8}>
				<div className="flex items-center justify-between px-4 py-3 border-b">
					<h3 className="font-semibold">Notifications</h3>
					{notifications.length > 0 && (
						<Button
							variant="ghost"
							size="sm"
							className="h-8 text-xs"
							onClick={clearAll}
						>
							<Trash2 className="h-3 w-3 mr-1" />
							Clear all
						</Button>
					)}
				</div>
				<div className="h-[400px] overflow-y-auto">
					{sortedNotifications.length === 0 ? (
						<div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
							<Bell className="h-8 w-8 mb-2 opacity-50" />
							<p className="text-sm">No notifications</p>
						</div>
					) : (
						<div className="p-2 space-y-2">
							{sortedNotifications.map((notification) => (
								<NotificationItem
									key={notification.id}
									notification={notification}
									onDismiss={() =>
										removeNotification(notification.id)
									}
									onNavigate={() =>
										handleNavigate(notification)
									}
								/>
							))}
						</div>
					)}
				</div>
			</PopoverContent>
		</Popover>
	);
}
