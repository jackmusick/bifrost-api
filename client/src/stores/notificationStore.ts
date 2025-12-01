import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * Notification Center store using Zustand with localStorage persistence
 *
 * Stores generic notifications that can be added by various sources (SDK scanner, etc.)
 * Notifications persist across sessions and can be dismissed individually or cleared.
 */

export type NotificationStatus = "success" | "error" | "warning" | "info";

export interface Notification {
	id: string;
	title: string; // Linkable title
	status: NotificationStatus;
	body: string;
	link?: string; // Optional navigation target (e.g., file path in editor)
	sourceFile?: string; // Source file for grouping/replacing on re-scan
	createdAt: string; // ISO timestamp
}

interface NotificationState {
	notifications: Notification[];

	// Actions
	addNotification: (
		notification: Omit<Notification, "id" | "createdAt">,
	) => void;
	removeNotification: (id: string) => void;
	clearAll: () => void;
	clearBySourceFile: (sourceFile: string) => void;
	replaceForSourceFile: (
		sourceFile: string,
		notifications: Omit<Notification, "id" | "createdAt">[],
	) => void;
}

export const useNotificationStore = create<NotificationState>()(
	persist(
		(set, get) => ({
			notifications: [],

			addNotification: (notification) => {
				const id = crypto.randomUUID();
				const newNotification: Notification = {
					...notification,
					id,
					createdAt: new Date().toISOString(),
				};
				set((state) => ({
					notifications: [newNotification, ...state.notifications],
				}));
			},

			removeNotification: (id) => {
				set((state) => ({
					notifications: state.notifications.filter(
						(n) => n.id !== id,
					),
				}));
			},

			clearAll: () => {
				set({ notifications: [] });
			},

			clearBySourceFile: (sourceFile) => {
				set((state) => ({
					notifications: state.notifications.filter(
						(n) => n.sourceFile !== sourceFile,
					),
				}));
			},

			replaceForSourceFile: (sourceFile, notifications) => {
				// Remove existing notifications for this source file and add new ones
				const existingOther = get().notifications.filter(
					(n) => n.sourceFile !== sourceFile,
				);
				const newNotifications: Notification[] = notifications.map(
					(n) => ({
						...n,
						id: crypto.randomUUID(),
						createdAt: new Date().toISOString(),
						sourceFile,
					}),
				);
				set({
					notifications: [...newNotifications, ...existingOther],
				});
			},
		}),
		{
			name: "bifrost-notifications",
			version: 1,
		},
	),
);

// Helper to get notification count by status
export const getNotificationCounts = (notifications: Notification[]) => {
	return {
		error: notifications.filter((n) => n.status === "error").length,
		warning: notifications.filter((n) => n.status === "warning").length,
		info: notifications.filter((n) => n.status === "info").length,
		success: notifications.filter((n) => n.status === "success").length,
		total: notifications.length,
	};
};
