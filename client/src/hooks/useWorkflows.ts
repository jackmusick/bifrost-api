/**
 * React Query hooks for workflows
 */

import { useQuery, useMutation } from "@tanstack/react-query";
import { workflowsService } from "@/services/workflows";
import { dataProvidersService } from "@/services/dataProviders";
import { toast } from "sonner";
import { useWorkflowsStore } from "@/stores/workflowsStore";

/**
 * Fetch workflow and data provider metadata.
 *
 * Note: Workflows and data providers are platform-wide resources (not org-scoped).
 * They are loaded from the file system and shared across all organizations.
 * The org scope only affects workflow EXECUTIONS (stored per-org), not the
 * workflows themselves.
 */
export function useWorkflowsMetadata() {
	const setWorkflows = useWorkflowsStore((state) => state.setWorkflows);

	return useQuery({
		queryKey: ["workflows", "metadata"],
		queryFn: async () => {
			// Fetch both workflows and data providers in parallel
			const [workflows, dataProviders] = await Promise.all([
				workflowsService.getWorkflows(),
				dataProvidersService.getAllProviders(),
			]);

			// Update Zustand store for global file type detection
			if (workflows) {
				setWorkflows(workflows);
			}

			// Return combined metadata
			return {
				workflows: workflows || [],
				dataProviders: dataProviders || [],
			};
		},
		// Cache for 1 minute - workflows don't change often
		staleTime: 60000,
	});
}

export function useExecuteWorkflow() {
	return useMutation({
		mutationFn: ({
			workflowName,
			inputData,
			transient,
			code,
			scriptName,
		}: {
			workflowName?: string;
			inputData?: Record<string, unknown>;
			transient?: boolean;
			code?: string;
			scriptName?: string;
		}) =>
			workflowsService.executeWorkflow(
				workflowName,
				inputData || {},
				transient,
				code,
				scriptName,
			),
		// Note: onSuccess toast removed - let caller handle toasts based on sync vs async
		// RunPanel shows different toasts for sync (immediate success) vs async (started)
		onError: (error: Error) => {
			toast.error("Failed to execute workflow", {
				description: error.message,
			});
		},
	});
}

/**
 * Incrementally reload a single workflow file
 * Used when a file is saved in the editor to update workflows store
 * without triggering a full workspace scan
 */
export function useReloadWorkflowFile() {
	const setWorkflows = useWorkflowsStore((state) => state.setWorkflows);

	return useMutation({
		mutationFn: async (filePath: string) => {
			// Call API with reload_file query param
			const workflows = await workflowsService.getWorkflows(filePath);
			return workflows;
		},
		onSuccess: (workflows) => {
			// Update store with refreshed workflow list
			if (workflows) {
				setWorkflows(workflows);
			}
		},
		onError: (error: Error) => {
			console.error("Failed to reload workflow file:", error);
			// Silent failure - don't show toast for background operations
		},
	});
}
