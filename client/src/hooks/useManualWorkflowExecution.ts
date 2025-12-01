/**
 * Hook for manually executing workflows in the form builder
 * Used for testing launch workflows before form publication
 */

import { useMutation } from "@tanstack/react-query";
import { workflowsService } from "@/services/workflows";
import { toast } from "sonner";

interface ExecuteWorkflowParams {
	workflowName: string;
	parameters?: Record<string, unknown>;
}

/**
 * Execute a workflow manually and return its results
 * Useful for testing launch workflows in the form builder
 */
export function useManualWorkflowExecution() {
	return useMutation({
		mutationFn: async ({
			workflowName,
			parameters = {},
		}: ExecuteWorkflowParams) => {
			return await workflowsService.executeWorkflow(
				workflowName,
				parameters,
			);
		},
		onError: (error: Error) => {
			toast.error("Failed to execute workflow", {
				description: error.message,
			});
		},
	});
}
