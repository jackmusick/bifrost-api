/**
 * Workspace Scanner service
 *
 * Scans workspace files for:
 * - SDK usage issues (config.get, secrets.get, oauth.get) with missing configurations
 * - Form validation errors (schema issues in form.json files)
 *
 * Publishes issues to notification center for user visibility.
 */

import { useNotificationStore } from "@/stores/notificationStore";

// Type definitions (will be replaced with auto-generated types after npm run generate:types)
export interface SDKUsageIssue {
	file_path: string;
	file_name: string;
	type: "config" | "secret" | "oauth";
	key: string;
	line_number: number;
}

export interface FormValidationIssue {
	file_path: string;
	file_name: string;
	form_name: string | null;
	error_message: string;
	field_name: string | null;
	field_index: number | null;
}

export interface WorkspaceScanResponse {
	issues: SDKUsageIssue[];
	scanned_files: number;
	// Form validation (added fields)
	form_issues: FormValidationIssue[];
	scanned_forms: number;
	valid_forms: number;
}

export interface FileScanRequest {
	file_path: string;
	content?: string;
}

const typeDescriptions: Record<string, string> = {
	config: "Config",
	secret: "Secret",
	oauth: "OAuth connection",
};

export const sdkScannerService = {
	/**
	 * Scan entire workspace for SDK usage issues
	 */
	async scanWorkspace(): Promise<WorkspaceScanResponse> {
		const response = await fetch("/api/workflows/scan", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
		});

		if (!response.ok) {
			throw new Error(`Failed to scan workspace: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Scan a single file for SDK usage issues
	 */
	async scanFile(request: FileScanRequest): Promise<WorkspaceScanResponse> {
		const response = await fetch("/api/workflows/scan/file", {
			method: "POST",
			headers: {
				"Content-Type": "application/json",
			},
			body: JSON.stringify(request),
		});

		if (!response.ok) {
			throw new Error(`Failed to scan file: ${response.statusText}`);
		}

		return response.json();
	},

	/**
	 * Scan workspace and publish issues to notification store
	 * Used on login and after git pull
	 *
	 * Handles both SDK usage issues and form validation errors.
	 */
	async scanWorkspaceAndNotify(): Promise<void> {
		try {
			const result = await this.scanWorkspace();
			const store = useNotificationStore.getState();

			// Track all source files we're updating (for cleanup)
			const updatedSourceFiles = new Set<string>();

			// 1. Process SDK usage issues
			const sdkNotifications = result.issues.map((issue) => ({
				title: issue.file_name,
				status: "error" as const,
				body: `Missing ${typeDescriptions[issue.type] || issue.type}: "${issue.key}" on line ${issue.line_number}`,
				link: issue.file_path,
				sourceFile: issue.file_path,
			}));

			// Group SDK issues by file
			const sdkFileGroups = new Map<
				string,
				typeof sdkNotifications
			>();
			for (const notif of sdkNotifications) {
				const existing = sdkFileGroups.get(notif.sourceFile!) || [];
				existing.push(notif);
				sdkFileGroups.set(notif.sourceFile!, existing);
				updatedSourceFiles.add(notif.sourceFile!);
			}

			// Replace SDK notifications for each file
			for (const [sourceFile, notifs] of sdkFileGroups) {
				store.replaceForSourceFile(sourceFile, notifs);
			}

			// 2. Process form validation issues
			const formIssues = result.form_issues || [];
			const formNotifications = formIssues.map((issue) => {
				// Build descriptive message
				let body = issue.error_message;
				if (issue.field_name) {
					body = `Field "${issue.field_name}": ${issue.error_message}`;
				} else if (issue.field_index !== null) {
					body = `Field ${issue.field_index}: ${issue.error_message}`;
				}

				return {
					title: issue.form_name || issue.file_name,
					status: "error" as const,
					body,
					link: issue.file_path,
					// Prefix with "form:" to distinguish from SDK issues
					sourceFile: `form:${issue.file_path}`,
				};
			});

			// Group form issues by file
			const formFileGroups = new Map<
				string,
				typeof formNotifications
			>();
			for (const notif of formNotifications) {
				const existing = formFileGroups.get(notif.sourceFile!) || [];
				existing.push(notif);
				formFileGroups.set(notif.sourceFile!, existing);
				updatedSourceFiles.add(notif.sourceFile!);
			}

			// Replace form notifications for each file
			for (const [sourceFile, notifs] of formFileGroups) {
				store.replaceForSourceFile(sourceFile, notifs);
			}

			// 3. Clear notifications for files that no longer have issues
			const existingSourceFiles = new Set(
				store.notifications
					.filter((n) => n.sourceFile)
					.map((n) => n.sourceFile!),
			);
			for (const sourceFile of existingSourceFiles) {
				if (!updatedSourceFiles.has(sourceFile)) {
					store.clearBySourceFile(sourceFile);
				}
			}

			// Log summary if there are issues
			const totalIssues = result.issues.length + formIssues.length;
			if (totalIssues > 0) {
				console.warn(
					`Workspace scan: ${result.scanned_files} files/${result.issues.length} SDK issues, ` +
						`${result.scanned_forms || 0} forms/${formIssues.length} form issues`,
				);
			}
		} catch (error) {
			console.error("Failed to scan workspace:", error);
		}
	},

	/**
	 * Scan a single file and update notifications
	 * Used after file save
	 */
	async scanFileAndNotify(filePath: string, content?: string): Promise<void> {
		try {
			const request: FileScanRequest = { file_path: filePath };
			if (content !== undefined) {
				request.content = content;
			}
			const result = await this.scanFile(request);

			const store = useNotificationStore.getState();

			// Convert issues to notifications
			const notifications = result.issues.map((issue) => ({
				title: issue.file_name,
				status: "error" as const,
				body: `Missing ${typeDescriptions[issue.type] || issue.type}: "${issue.key}" on line ${issue.line_number}`,
				link: issue.file_path,
				sourceFile: issue.file_path,
			}));

			// Replace all notifications for this file
			store.replaceForSourceFile(filePath, notifications);

			// Only log if there are issues (using allowed console.warn)
			if (result.issues.length > 0) {
				console.warn(
					`SDK file scan: ${filePath}, ${result.issues.length} issues found`,
				);
			}
		} catch (error) {
			console.error(
				`Failed to scan file ${filePath} for SDK usage:`,
				error,
			);
		}
	},
};
